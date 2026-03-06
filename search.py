"""歌曲搜索 + 最佳匹配评分"""

from difflib import SequenceMatcher
from pyncm.apis.cloudsearch import GetSearchResult
from config import SEARCH_LIMIT
from utils import retry, rate_limiter


def _similarity(a: str, b: str) -> float:
    """计算两个字符串的相似度 (0~1)"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _score_match(candidate: dict, name: str, artist: str = "", album: str = "") -> float:
    """对搜索结果候选项评分

    评分权重：
    - 歌名匹配: 60%
    - 歌手匹配: 30%
    - 专辑匹配: 10%
    """
    c_name = candidate.get("name", "")
    c_artists = " ".join(a.get("name", "") for a in candidate.get("ar", candidate.get("artists", [])))
    c_album = candidate.get("al", candidate.get("album", {})).get("name", "")

    name_score = _similarity(name, c_name) * 0.6
    artist_score = 0.0
    if artist:
        artist_score = _similarity(artist, c_artists) * 0.3
    else:
        artist_score = 0.15  # 未提供歌手时给一半分
    album_score = 0.0
    if album:
        album_score = _similarity(album, c_album) * 0.1
    else:
        album_score = 0.05

    return name_score + artist_score + album_score


@retry()
def search_song(name: str, artist: str = "", album: str = "") -> dict | None:
    """搜索歌曲并返回最佳匹配结果

    返回格式:
    {
        "song_id": int,
        "name": str,
        "artist": str,
        "album": str,
        "duration": int,  # 毫秒
        "score": float,
    }
    或 None（未找到）
    """
    rate_limiter.wait()

    # 构建搜索关键词
    keyword = name
    if artist:
        keyword = f"{name} {artist}"

    result = GetSearchResult(keyword, stype=1, limit=SEARCH_LIMIT)

    songs = result.get("result", {}).get("songs", [])
    if not songs:
        return None

    # 评分并选择最佳匹配
    best = None
    best_score = 0.0

    for song in songs:
        score = _score_match(song, name, artist, album)
        if score > best_score:
            best_score = score
            best = song

    if not best or best_score < 0.3:
        return None

    artists = best.get("ar", best.get("artists", []))
    artist_name = ", ".join(a.get("name", "") for a in artists)
    album_info = best.get("al", best.get("album", {}))

    return {
        "song_id": best["id"],
        "name": best.get("name", ""),
        "artist": artist_name,
        "album": album_info.get("name", ""),
        "duration": best.get("dt", best.get("duration", 0)),
        "score": round(best_score, 3),
    }


def batch_search(songs: list[dict], tracker=None, on_progress=None) -> list[dict]:
    """批量搜索歌曲

    songs: [{"name": ..., "artist": ..., "album": ..., "category": ...}, ...]
    tracker: ProgressTracker 实例（支持断点续搜）
    on_progress: 回调函数 (index, total, result)

    返回: [{"input": {...}, "result": {...} or None}, ...]
    """
    results = []
    total = len(songs)

    for i, song in enumerate(songs):
        name = song["name"]
        artist = song.get("artist", "")
        album = song.get("album", "")

        # 检查是否已搜索过（断点续搜）
        if tracker and tracker.is_searched(name, artist):
            cached = tracker.get_search_result(name, artist)
            results.append({"input": song, "result": cached})
            if on_progress:
                on_progress(i, total, cached)
            continue

        # 执行搜索
        try:
            result = search_song(name, artist, album)
        except Exception as e:
            result = None
            print(f"  搜索失败 [{name}]: {e}")

        # 记录进度
        if tracker:
            tracker.mark_searched(name, artist, result)

        results.append({"input": song, "result": result})

        if on_progress:
            on_progress(i, total, result)

    return results
