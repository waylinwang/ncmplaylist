"""配置常量"""

import os
import sys


def get_data_dir() -> str:
    """获取可写的数据目录（解决 macOS App Translocation 只读问题）"""
    if getattr(sys, '_MEIPASS', None):
        # PyInstaller 打包环境 → 写到用户目录
        d = os.path.join(os.path.expanduser("~"), ".neteasymusic")
    else:
        # 开发环境 → 写到项目目录
        d = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(d, exist_ok=True)
    return d


def get_downloads_dir(custom_dir: str = "") -> str:
    """获取下载目录，支持自定义路径，默认桌面 ncmdownloads"""
    if custom_dir:
        d = custom_dir
    else:
        d = os.path.join(os.path.expanduser("~/Desktop"), "ncmdownloads")
    os.makedirs(d, exist_ok=True)
    return d


def get_app_dir() -> str:
    """获取应用资源目录（只读，用于读取模板等）"""
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


# 音质设置 (bitrate)
BITRATE = 320000  # 320kbps VIP 音质

# 歌单设置
PLAYLIST_MAX_SONGS = 500  # 每个歌单最多歌曲数

# 速率限制
REQUEST_INTERVAL = 0.8  # 请求间隔（秒）
RATE_LIMIT_WAIT = 30  # 遇到限流时等待秒数

# 重试设置
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # 指数退避基础延迟（秒）

# 搜索设置
SEARCH_LIMIT = 10  # 每次搜索返回的结果数

# 文件路径
DOWNLOADS_DIR = "downloads"
PROGRESS_FILE = "progress.json"
SESSION_FILE = ".session_cache"
REPORT_FILE = "result_report.xlsx"

# 默认歌单名称
DEFAULT_PLAYLIST_NAME = "批量导入歌单"

# 文件名最大长度
MAX_FILENAME_LENGTH = 200
