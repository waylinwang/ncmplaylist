"""下载引擎：流式下载 + 元数据写入"""

import os
import requests
from pyncm.apis.track import GetTrackAudio, GetTrackDetail
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, ID3NoHeaderError

from config import BITRATE, DOWNLOADS_DIR
from utils import retry, rate_limiter, sanitize_filename


@retry()
def get_song_url(song_id: int, bitrate: int = BITRATE) -> dict | None:
    """获取歌曲下载链接

    返回: {"url": str, "type": str, "br": int} 或 None
    """
    rate_limiter.wait()
    result = GetTrackAudio(song_ids=[song_id], bitrate=bitrate)
    data_list = result.get("data", [])
    if not data_list:
        return None

    info = data_list[0]
    url = info.get("url")
    if not url:
        return None

    return {
        "url": url,
        "type": info.get("type", "mp3"),
        "br": info.get("br", 0),
    }


@retry()
def get_song_detail(song_id: int) -> dict | None:
    """获取歌曲详情（含封面图片URL）"""
    rate_limiter.wait()
    result = GetTrackDetail(song_ids=[song_id])
    songs = result.get("songs", [])
    if not songs:
        return None
    song = songs[0]
    artists = song.get("ar", [])
    album = song.get("al", {})
    return {
        "name": song.get("name", ""),
        "artist": ", ".join(a.get("name", "") for a in artists),
        "album": album.get("name", ""),
        "cover_url": album.get("picUrl", ""),
    }


def download_song(song_id: int, category: str = "", base_dir: str = None, bitrate: int = BITRATE) -> str | None:
    """下载单首歌曲到本地

    返回文件路径，失败返回 None
    """
    from config import get_downloads_dir
    base_dir = base_dir or get_downloads_dir()

    # 获取下载链接
    audio_info = get_song_url(song_id, bitrate=bitrate)
    if not audio_info:
        return None

    url = audio_info["url"]
    file_type = audio_info.get("type", "mp3") or "mp3"
    bitrate = audio_info.get("br", 0)

    # 检查是否为试听版（低码率）
    if bitrate and bitrate < 128000:
        print(f"  警告: 歌曲 {song_id} 码率仅 {bitrate // 1000}kbps，可能为试听版")

    # 获取歌曲详情
    detail = get_song_detail(song_id)
    if not detail:
        detail = {"name": str(song_id), "artist": "未知", "album": "", "cover_url": ""}

    # 构建文件路径
    artist_name = sanitize_filename(detail["artist"])
    song_name = sanitize_filename(detail["name"])
    filename = f"{artist_name} - {song_name}.{file_type}"

    if category:
        save_dir = os.path.join(base_dir, sanitize_filename(category))
    else:
        save_dir = base_dir

    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, filename)

    # 如果文件已存在，跳过
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    # 流式下载
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        temp_path = file_path + ".tmp"
        with open(temp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        os.rename(temp_path, file_path)
    except Exception as e:
        # 清理临时文件
        temp_path = file_path + ".tmp"
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

    # 写入元数据（仅 mp3）
    if file_type.lower() == "mp3":
        _write_metadata(file_path, detail)

    return file_path


def _write_metadata(file_path: str, detail: dict):
    """写入 ID3 元数据"""
    try:
        try:
            audio = MP3(file_path, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()

        audio.tags.add(TIT2(encoding=3, text=detail.get("name", "")))
        audio.tags.add(TPE1(encoding=3, text=detail.get("artist", "")))
        audio.tags.add(TALB(encoding=3, text=detail.get("album", "")))

        # 下载封面
        cover_url = detail.get("cover_url", "")
        if cover_url:
            try:
                cover_data = requests.get(cover_url, timeout=10).content
                audio.tags.add(APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=cover_data,
                ))
            except Exception:
                pass  # 封面下载失败不影响主流程

        audio.save()
    except Exception:
        pass  # 元数据写入失败不影响主流程
