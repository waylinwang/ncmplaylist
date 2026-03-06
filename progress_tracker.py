"""断点续传：通过 progress.json 记录搜索和下载状态"""

import os
import json
from config import PROGRESS_FILE, get_data_dir


class ProgressTracker:
    """跟踪搜索和下载进度，支持断点续传"""

    def __init__(self, task_id: str = "default"):
        self.task_id = task_id
        self.path = os.path.join(get_data_dir(), PROGRESS_FILE)
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
                return all_data.get(self.task_id, self._default())
            except (json.JSONDecodeError, KeyError):
                pass
        return self._default()

    def _default(self) -> dict:
        return {
            "searched": {},    # {input_key: {song_id, matched_name, matched_artist, ...} or None}
            "downloaded": {},  # {song_id: file_path}
            "playlisted": {},  # {playlist_name: playlist_id}
            "total_songs": 0,
        }

    def save(self):
        """持久化进度"""
        all_data = {}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            except (json.JSONDecodeError, KeyError):
                pass
        all_data[self.task_id] = self.data
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def make_key(name: str, artist: str = "") -> str:
        """生成歌曲唯一键"""
        return f"{name.strip()}|{artist.strip()}".lower()

    def is_searched(self, name: str, artist: str = "") -> bool:
        return self.make_key(name, artist) in self.data["searched"]

    def get_search_result(self, name: str, artist: str = "") -> dict | None:
        return self.data["searched"].get(self.make_key(name, artist))

    def mark_searched(self, name: str, artist: str, result: dict | None):
        """记录搜索结果，result 为 None 表示未找到"""
        self.data["searched"][self.make_key(name, artist)] = result
        self.save()

    def is_downloaded(self, song_id) -> bool:
        return str(song_id) in self.data["downloaded"]

    def get_download_path(self, song_id) -> str | None:
        return self.data["downloaded"].get(str(song_id))

    def mark_downloaded(self, song_id, file_path: str):
        self.data["downloaded"][str(song_id)] = file_path
        self.save()

    def is_playlisted(self, playlist_name: str) -> bool:
        return playlist_name in self.data["playlisted"]

    def get_playlist_id(self, playlist_name: str) -> int | None:
        return self.data["playlisted"].get(playlist_name)

    def mark_playlisted(self, playlist_name: str, playlist_id: int):
        self.data["playlisted"][playlist_name] = playlist_id
        self.save()

    def set_total(self, total: int):
        self.data["total_songs"] = total
        self.save()

    def summary(self) -> dict:
        searched = self.data["searched"]
        found = sum(1 for v in searched.values() if v is not None)
        not_found = sum(1 for v in searched.values() if v is None)
        return {
            "total": self.data["total_songs"],
            "searched": len(searched),
            "found": found,
            "not_found": not_found,
            "downloaded": len(self.data["downloaded"]),
            "playlists_created": len(self.data["playlisted"]),
        }

    def clear(self):
        """清除进度"""
        self.data = self._default()
        self.save()
