#!/bin/bash
# 双击此文件启动网易云音乐批量下载工具
cd "$(dirname "$0")"
echo "========================================"
echo "  网易云音乐批量下载工具"
echo "  浏览器将自动打开..."
echo "  关闭此窗口即可停止"
echo "========================================"
echo ""

# 检查虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 启动并打开浏览器
open "http://localhost:8501" &
streamlit run app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false
