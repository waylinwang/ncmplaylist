# NCM Playlist - 网易云音乐批量下载工具

批量搜索、下载网易云音乐歌曲并自动创建歌单。支持 Web 界面和命令行两种使用方式。

## 功能特性

- **批量搜索** - 从 Excel/CSV 导入歌曲列表，智能匹配（歌名 60% + 歌手 30% + 专辑 10%）
- **批量下载** - 支持多种音质（128kbps / 192kbps / 320kbps / 无损 FLAC）
- **自动建歌单** - 按分类自动创建网易云歌单，已有同名歌单自动跳过
- **断点续传** - 中断后可从上次进度继续
- **QR 扫码登录** - 手机扫码，会话自动缓存
- **Web 界面** - Streamlit 可视化操作，适合非开发人员
- **CLI 命令行** - 适合批量自动化处理
- **macOS 打包** - PyInstaller 一键打包为 `.app`

## 截图

### 登录页 - QR 扫码登录

![登录页](screenshots/login.png)

### 主界面 - 上传歌曲列表 & 配置

![主界面](screenshots/main.png)

## 快速开始

### 环境要求

- Python 3.10+
- 网易云音乐 VIP 账号（下载高品质音乐需要）

### 安装

```bash
git clone https://github.com/your-username/ncmplaylist.git
cd ncmplaylist
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Web 界面（推荐）

```bash
streamlit run app.py
```

浏览器打开 `http://localhost:8501`，扫码登录后上传歌曲列表即可。

### 命令行

```bash
# 生成 Excel 模板
python main.py template

# 扫码登录
python main.py login

# 执行批量下载（搜索 + 下载 + 建歌单）
python main.py run songs.xlsx

# 仅搜索 + 建歌单（不下载）
python main.py run songs.xlsx --no-download

# 仅搜索 + 下载（不建歌单）
python main.py run songs.xlsx --no-playlist

# 断点续传
python main.py run songs.xlsx --resume

# 指定音质（无损）
python main.py run songs.xlsx --bitrate 999000

# 查看进度
python main.py report
```

## Excel 模板格式

| 歌曲名称 | 歌手 | 专辑 | 分类/歌单 | 备注 |
|---------|------|------|----------|------|
| 晴天 | 周杰伦 | 叶惠美 | 华语经典 | |
| 夜曲 | 周杰伦 | 十一月的萧邦 | 华语经典 | |
| Shape of You | Ed Sheeran | | 欧美流行 | |

- **歌曲名称**（必填）
- **歌手** - 提高匹配准确率
- **专辑** - 可选，辅助匹配
- **分类/歌单** - 自动按此分类创建歌单
- **备注** - 不参与处理

## 音质选项

| 选项 | Bitrate | 说明 |
|------|---------|------|
| 标准 | 128kbps | 普通用户可用 |
| 高品 | 192kbps | - |
| 极高 | 320kbps | VIP（默认） |
| 无损 | FLAC | VIP |

## macOS 打包

```bash
python build_mac.py
```

生成 `dist/neteasymusic.app`，双击即可运行。

## 项目结构

```
ncmplaylist/
├── app.py                 # Streamlit Web 界面
├── main.py                # CLI 命令行入口
├── config.py              # 配置常量
├── auth.py                # QR 扫码登录 & 会话管理
├── search.py              # 歌曲搜索 & 智能匹配
├── downloader.py          # 歌曲下载 & 元数据写入
├── playlist_manager.py    # 歌单创建（自动去重）
├── excel_handler.py       # Excel/CSV 读写
├── progress_tracker.py    # 断点续传进度跟踪
├── utils.py               # 重试、限流、工具函数
├── launcher.py            # PyInstaller 启动入口
├── build_mac.py           # macOS 打包脚本
├── requirements.txt       # Python 依赖
├── 启动工具.command        # macOS 双击启动脚本
└── template/              # Excel 模板
```

## 注意事项

- 下载高品质音乐需要网易云 VIP 账号
- 为避免 API 限流，请求间隔默认 0.8 秒
- 每个歌单最多 500 首歌曲，超出自动分批
- 会话缓存在 `.session_cache` 文件中，删除可重新登录
- 本工具仅供个人学习研究使用

## License

MIT
