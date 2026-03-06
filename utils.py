"""工具函数：重试装饰器、限速器、文件名清理"""

import re
import time
import functools
from config import MAX_RETRIES, RETRY_BASE_DELAY, REQUEST_INTERVAL, RATE_LIMIT_WAIT, MAX_FILENAME_LENGTH


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    # 替换非法字符
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    # 移除前后空格和点
    name = name.strip(' .')
    # 截断过长文件名
    if len(name) > MAX_FILENAME_LENGTH:
        name = name[:MAX_FILENAME_LENGTH]
    return name or "unknown"


def retry(max_retries=MAX_RETRIES, base_delay=RETRY_BASE_DELAY):
    """指数退避重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        error_msg = str(e).lower()
                        # 速率限制特殊处理
                        if '429' in error_msg or '503' in error_msg:
                            delay = RATE_LIMIT_WAIT
                            print(f"  遇到速率限制，等待 {delay}s 后重试...")
                        else:
                            print(f"  请求失败({e})，{delay}s 后重试 ({attempt + 1}/{max_retries})...")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


class RateLimiter:
    """简单的速率限制器"""

    def __init__(self, interval=REQUEST_INTERVAL):
        self.interval = interval
        self._last_call = 0.0

    def wait(self):
        """确保两次调用之间有足够间隔"""
        now = time.time()
        elapsed = now - self._last_call
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self._last_call = time.time()


# 全局限速器实例
rate_limiter = RateLimiter()
