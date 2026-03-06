"""创建歌单 & 添加歌曲"""

from pyncm.apis.playlist import SetCreatePlaylist, SetManipulatePlaylistTracks
from pyncm.apis.user import GetUserPlaylists
from pyncm.apis.login import GetCurrentLoginStatus
from config import PLAYLIST_MAX_SONGS, DEFAULT_PLAYLIST_NAME
from utils import retry, rate_limiter


def _get_user_id() -> int | None:
    """获取当前登录用户 ID"""
    try:
        status = GetCurrentLoginStatus()
        profile = status.get("profile") or status.get("content", {}).get("profile")
        if profile:
            return profile.get("userId")
        account = status.get("account")
        if account:
            return account.get("id")
    except Exception:
        pass
    return None


def _get_existing_playlists() -> dict[str, int]:
    """获取用户已有歌单名称 -> ID 映射"""
    uid = _get_user_id()
    if not uid:
        return {}
    try:
        rate_limiter.wait()
        result = GetUserPlaylists(uid, limit=1001)
        playlists = result.get("playlist", [])
        return {p["name"]: p["id"] for p in playlists if p.get("name")}
    except Exception:
        return {}


@retry()
def create_playlist(name: str) -> int | None:
    """创建歌单，返回歌单 ID"""
    rate_limiter.wait()
    result = SetCreatePlaylist(name)
    playlist_id = result.get("id")
    if not playlist_id:
        # 某些版本返回格式不同
        playlist_id = result.get("playlist", {}).get("id")
    return playlist_id


@retry()
def add_songs_to_playlist(playlist_id: int, song_ids: list[int]):
    """向歌单添加歌曲"""
    rate_limiter.wait()
    if not song_ids:
        return
    result = SetManipulatePlaylistTracks(song_ids, playlist_id, op="add")
    return result


def batch_create_playlists(
    songs_by_category: dict[str, list[int]],
    tracker=None,
    prefix: str = "",
) -> dict[str, int]:
    """批量创建歌单并添加歌曲

    songs_by_category: {"分类名": [song_id, ...], ...}
    tracker: ProgressTracker
    prefix: 歌单名称前缀

    返回: {"歌单名": playlist_id, ...}
    """
    created = {}

    # 获取用户已有歌单，用于去重
    existing = _get_existing_playlists()
    if existing:
        print(f"  已获取用户歌单列表 ({len(existing)} 个)")

    for category, song_ids in songs_by_category.items():
        if not song_ids:
            continue

        # 按 PLAYLIST_MAX_SONGS 分批
        chunks = [song_ids[i:i + PLAYLIST_MAX_SONGS] for i in range(0, len(song_ids), PLAYLIST_MAX_SONGS)]

        for idx, chunk in enumerate(chunks):
            if len(chunks) == 1:
                playlist_name = f"{prefix}{category}" if prefix else category
            else:
                playlist_name = f"{prefix}{category} ({idx + 1})" if prefix else f"{category} ({idx + 1})"

            # 检查是否已创建（断点续传）
            if tracker and tracker.is_playlisted(playlist_name):
                pid = tracker.get_playlist_id(playlist_name)
                print(f"  歌单已存在(本地记录): {playlist_name} (ID: {pid})")
                created[playlist_name] = pid
                continue

            # 检查网易云账号是否已有同名歌单
            if playlist_name in existing:
                pid = existing[playlist_name]
                print(f"  歌单已存在(云端): {playlist_name} (ID: {pid})，跳过创建")
                if tracker:
                    tracker.mark_playlisted(playlist_name, pid)
                created[playlist_name] = pid
                continue

            print(f"  创建歌单: {playlist_name} ({len(chunk)} 首)")
            try:
                pid = create_playlist(playlist_name)
                if not pid:
                    print(f"  创建歌单失败: {playlist_name}")
                    continue

                # 分批添加歌曲（每次最多 100 首）
                batch_size = 100
                for i in range(0, len(chunk), batch_size):
                    batch = chunk[i:i + batch_size]
                    add_songs_to_playlist(pid, batch)

                if tracker:
                    tracker.mark_playlisted(playlist_name, pid)
                created[playlist_name] = pid
                print(f"  歌单创建成功: {playlist_name} (ID: {pid})")

            except Exception as e:
                print(f"  歌单创建失败 [{playlist_name}]: {e}")

    return created
