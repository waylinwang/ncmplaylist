"""PyInstaller 启动入口 - 启动 Streamlit 并打开浏览器"""

import os
import sys
import socket
import signal
import subprocess
import threading
import time
import webbrowser


def get_base_dir():
    """获取资源文件所在目录"""
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def _kill_port(port: int):
    """杀掉占用指定端口的进程"""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
        if pids:
            time.sleep(1)
    except Exception:
        pass


def main():
    base_dir = get_base_dir()
    app_path = os.path.join(base_dir, "app.py")
    port = 8501

    # 设置工作目录到 base_dir，确保模块导入正常
    os.chdir(base_dir)

    # 如果端口被占用，先杀掉旧进程
    if _is_port_in_use(port):
        print(f"端口 {port} 已被占用，正在释放...")
        _kill_port(port)
        # 等待端口释放
        for _ in range(10):
            if not _is_port_in_use(port):
                break
            time.sleep(0.5)
        if _is_port_in_use(port):
            print(f"端口 {port} 无法释放，请手动关闭占用进程后重试")
            input("按回车键退出...")
            return

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
