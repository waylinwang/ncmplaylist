"""PyInstaller 启动入口 - 启动 Streamlit 并打开浏览器"""

import os
import sys
import subprocess
import threading
import time
import webbrowser


def get_base_dir():
    """获取资源文件所在目录"""
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def main():
    base_dir = get_base_dir()
    app_path = os.path.join(base_dir, "app.py")
    port = 8501

    # 设置工作目录到 base_dir，确保模块导入正常
    os.chdir(base_dir)

    # 延迟打开浏览器
    def open_browser():
        time.sleep(3)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    print(f"正在启动网易云音乐批量下载工具...")
    print(f"浏览器将自动打开 http://localhost:{port}")
    print("关闭此窗口即可停止服务\n")

    # 用 streamlit 的 Python API 启动
    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit", "run", app_path,
        "--server.headless", "true",
        "--server.address", "localhost",
        "--server.port", str(port),
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
    ]
    stcli.main()


if __name__ == "__main__":
    main()
