"""配置常量"""

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
