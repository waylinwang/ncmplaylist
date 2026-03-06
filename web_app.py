"""Streamlit Web 界面 - 网易云音乐批量下载工具"""

import os
import io
import time
import base64
import zipfile
from collections import defaultdict

import streamlit as st
import qrcode
from PIL import Image

from pyncm.apis.login import LoginQrcodeUnikey, LoginQrcodeCheck, GetLoginQRCodeUrl

from auth import load_session, save_session, _get_profile, check_login
from excel_handler import generate_template, read_song_list, generate_report
from search import search_song
from downloader import download_song
from playlist_manager import batch_create_playlists
from progress_tracker import ProgressTracker
from config import DEFAULT_PLAYLIST_NAME, REPORT_FILE

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="网易云音乐批量下载工具",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- 全局样式 ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');

/* 全局字体 */
html, body, [class*="css"] {
    font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 隐藏默认 header/footer */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}

/* ===== 登录页样式 ===== */
.login-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 70vh;
    padding: 2rem;
}

.login-card {
    background: linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 24px;
    padding: 3rem 3.5rem;
    max-width: 440px;
    width: 100%;
    box-shadow:
        0 20px 60px rgba(0,0,0,0.3),
        0 0 0 1px rgba(255,255,255,0.05),
        inset 0 1px 0 rgba(255,255,255,0.1);
    text-align: center;
    position: relative;
    overflow: hidden;
}

.login-card::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 20%, rgba(229,57,53,0.08) 0%, transparent 50%),
                radial-gradient(circle at 70% 80%, rgba(66,133,244,0.06) 0%, transparent 50%);
    pointer-events: none;
}

.login-card > * { position: relative; z-index: 1; }

.login-brand {
    font-size: 1.1rem;
    font-weight: 300;
    color: rgba(255,255,255,0.5);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}

.login-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 2rem;
    line-height: 1.3;
}

.login-title span {
    background: linear-gradient(135deg, #e53935, #ff6f61);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.qr-container {
    background: #fff;
    border-radius: 16px;
    padding: 16px;
    display: inline-block;
    margin: 0 auto 1.5rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}

.qr-container img {
    display: block;
    width: 200px;
    height: 200px;
}

.scan-steps {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 1.5rem;
    text-align: left;
}

.scan-step {
    display: flex;
    align-items: center;
    gap: 12px;
    color: rgba(255,255,255,0.6);
    font-size: 0.85rem;
    transition: all 0.3s ease;
}

.scan-step.active {
    color: #fff;
}

.scan-step.done {
    color: #4caf50;
}

.step-dot {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    flex-shrink: 0;
    background: rgba(255,255,255,0.08);
    border: 1.5px solid rgba(255,255,255,0.15);
    transition: all 0.3s ease;
}

.scan-step.active .step-dot {
    background: rgba(229,57,53,0.2);
    border-color: #e53935;
    color: #e53935;
    box-shadow: 0 0 12px rgba(229,57,53,0.3);
}

.scan-step.done .step-dot {
    background: rgba(76,175,80,0.2);
    border-color: #4caf50;
    color: #4caf50;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 20px;
    border-radius: 100px;
    font-size: 0.85rem;
    font-weight: 500;
    margin-top: 1rem;
}

.status-waiting {
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.7);
    border: 1px solid rgba(255,255,255,0.1);
}

.status-scanned {
    background: rgba(66,133,244,0.15);
    color: #90caf9;
    border: 1px solid rgba(66,133,244,0.3);
    animation: pulse-blue 2s infinite;
}

.status-success {
    background: rgba(76,175,80,0.15);
    color: #a5d6a7;
    border: 1px solid rgba(76,175,80,0.3);
}

.status-expired {
    background: rgba(255,152,0,0.15);
    color: #ffcc80;
    border: 1px solid rgba(255,152,0,0.3);
}

@keyframes pulse-blue {
    0%, 100% { box-shadow: 0 0 0 0 rgba(66,133,244,0.2); }
    50% { box-shadow: 0 0 0 8px rgba(66,133,244,0); }
}

.dot-pulse {
    display: inline-block;
    animation: dot-blink 1.4s infinite;
}
.dot-pulse:nth-child(2) { animation-delay: 0.2s; }
.dot-pulse:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-blink {
    0%, 80%, 100% { opacity: 0.2; }
    40% { opacity: 1; }
}

/* ===== 已登录用户卡片 ===== */
.user-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    align-items: center;
    gap: 14px;
    border: 1px solid rgba(255,255,255,0.08);
}

.user-avatar {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: linear-gradient(135deg, #e53935, #ff6f61);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 1.1rem;
    font-weight: 700;
    flex-shrink: 0;
}

.user-info { flex: 1; min-width: 0; }

.user-name {
    color: #fff;
    font-weight: 600;
    font-size: 0.95rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.user-vip {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    display: inline-block;
    margin-top: 4px;
}
.user-vip.is-vip {
    background: linear-gradient(135deg, #f9a825, #ff8f00);
    color: #fff;
}
.user-vip.no-vip {
    background: rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.5);
}

/* ===== 指标卡片 ===== */
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #f8fafc, #f1f5f9);
    border-radius: 12px;
    padding: 16px 20px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

div[data-testid="stMetric"] label {
    color: #64748b !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #1e293b !important;
    font-weight: 700 !important;
}

/* ===== 侧边栏美化 ===== */
section[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}

section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: rgba(255,255,255,0.9) !important;
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}

section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.06);
}

section[data-testid="stSidebar"] .stDownloadButton > button,
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.06) !important;
    color: rgba(255,255,255,0.85) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

section[data-testid="stSidebar"] .stDownloadButton > button:hover,
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.12) !important;
    border-color: rgba(255,255,255,0.2) !important;
}
</style>
""", unsafe_allow_html=True)


# ---------- 会话状态初始化 ----------
def init_state():
    defaults = {
        "logged_in": False,
        "username": "",
        "vip": False,
        "qr_uuid": None,
        "qr_polling": False,
        "running": False,
        "log_lines": [],
        "search_results": [],
        "stats": {"total": 0, "found": 0, "not_found": 0, "downloaded": 0, "failed": 0, "playlists": 0},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ---------- 日志辅助 ----------
def log(msg: str):
    st.session_state.log_lines.append(msg)


# ---------- 登录相关 ----------
def try_restore_session():
    """尝试从缓存恢复登录"""
    if st.session_state.logged_in:
        return True
    if load_session():
        profile = _get_profile()
        if profile:
            st.session_state.logged_in = True
            st.session_state.username = profile.get("nickname", "未知用户")
            st.session_state.vip = profile.get("vipType", 0) > 0
            return True
    return False


def generate_qr_image(url: str) -> Image.Image:
    """生成二维码 PIL 图片"""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="#1a1a2e", back_color="#ffffff").convert("RGB")


def qr_image_to_base64(img: Image.Image) -> str:
    """PIL 图片转 base64"""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def render_sidebar_user():
    """侧边栏：用户信息"""
    if st.session_state.logged_in:
        username = st.session_state.username
        initial = username[0] if username else "?"
        vip_cls = "is-vip" if st.session_state.vip else "no-vip"
        vip_text = "VIP 会员" if st.session_state.vip else "普通用户"

        st.markdown(f"""
        <div class="user-card">
            <div class="user-avatar">{initial}</div>
            <div class="user-info">
                <div class="user-name">{username}</div>
                <span class="user-vip {vip_cls}">{vip_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("切换账号", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.vip = False
            st.session_state.qr_uuid = None
            st.session_state.qr_polling = False
            session_path = os.path.join(os.path.dirname(__file__), ".session_cache")
            if os.path.exists(session_path):
                os.remove(session_path)
            st.rerun()
    else:
        st.markdown("""
        <div style="color: rgba(255,255,255,0.5); font-size: 0.85rem; padding: 8px 0;">
            未登录 - 请在主页扫码
        </div>
        """, unsafe_allow_html=True)


def render_login_page():
    """主区域：全屏登录页"""

    # 生成二维码（如果还没有）
    if not st.session_state.qr_uuid:
        uuid_result = LoginQrcodeUnikey()
        uuid = uuid_result.get("unikey")
        if uuid:
            st.session_state.qr_uuid = uuid
            st.session_state.qr_polling = True
        else:
            st.error("获取二维码失败，请刷新页面重试")
            return

    qr_url = GetLoginQRCodeUrl(st.session_state.qr_uuid)
    qr_img = generate_qr_image(qr_url)
    qr_b64 = qr_image_to_base64(qr_img)

    # 检查扫码状态
    scan_status = "waiting"  # waiting / scanned / success / expired
    status_text = ""

    if st.session_state.qr_polling:
        try:
            check_result = LoginQrcodeCheck(st.session_state.qr_uuid)
            code = check_result.get("code", 0)

            if code == 803:
                scan_status = "success"
                try:
                    save_session()
                except Exception:
                    pass
                profile = _get_profile()
                st.session_state.logged_in = True
                st.session_state.username = profile.get("nickname", "未知用户") if profile else "未知用户"
                st.session_state.vip = (profile.get("vipType", 0) > 0) if profile else False
                st.session_state.qr_uuid = None
                st.session_state.qr_polling = False
                st.rerun()
                return
            elif code == 800:
                scan_status = "expired"
                st.session_state.qr_polling = False
            elif code == 802:
                scan_status = "scanned"
                status_text = "已扫码，请在手机上确认"
            else:
                scan_status = "waiting"
        except Exception:
            scan_status = "waiting"

    # 步骤状态
    step1_cls = "done" if scan_status in ("scanned", "success") else "active"
    step2_cls = "done" if scan_status == "success" else ("active" if scan_status == "scanned" else "")
    step3_cls = "active" if scan_status == "success" else ""

    step1_dot = "✓" if step1_cls == "done" else "1"
    step2_dot = "✓" if step2_cls == "done" else "2"
    step3_dot = "✓" if step3_cls == "done" else "3"

    # 状态徽章
    if scan_status == "waiting":
        badge_html = """<div class="status-badge status-waiting">
            <span class="dot-pulse">·</span><span class="dot-pulse">·</span><span class="dot-pulse">·</span>
            &nbsp;等待扫码
        </div>"""
    elif scan_status == "scanned":
        badge_html = f'<div class="status-badge status-scanned">📱 {status_text}</div>'
    elif scan_status == "expired":
        badge_html = '<div class="status-badge status-expired">⏳ 二维码已过期</div>'
    else:
        badge_html = '<div class="status-badge status-success">✓ 登录成功</div>'

    # 渲染登录卡片
    st.markdown(f"""
    <div class="login-wrapper">
        <div class="login-card">
            <div class="login-brand">NetEase Cloud Music</div>
            <div class="login-title">扫码<span>登录</span></div>

            <div class="qr-container">
                <img src="data:image/png;base64,{qr_b64}" alt="登录二维码" />
            </div>

            {badge_html}

            <div class="scan-steps">
                <div class="scan-step {step1_cls}">
                    <div class="step-dot">{step1_dot}</div>
                    打开网易云音乐 App
                </div>
                <div class="scan-step {step2_cls}">
                    <div class="step-dot">{step2_dot}</div>
                    扫描上方二维码
                </div>
                <div class="scan-step {step3_cls}">
                    <div class="step-dot">{step3_dot}</div>
                    在手机上确认登录
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 操作按钮
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        if scan_status == "expired":
            if st.button("🔄 刷新二维码", use_container_width=True, type="primary"):
                st.session_state.qr_uuid = None
                st.session_state.qr_polling = True
                st.rerun()
        elif scan_status in ("waiting", "scanned"):
            # 自动轮询：2 秒后自动刷新页面检查状态
            time.sleep(2)
            st.rerun()


# ---------- 核心执行流程 ----------
def run_pipeline(songs: list[dict], do_download: bool, do_playlist: bool, resume: bool):
    """执行搜索 + 下载 + 建歌单流程"""
    st.session_state.running = True
    st.session_state.log_lines = []
    st.session_state.search_results = []
    stats = {"total": len(songs), "found": 0, "not_found": 0, "downloaded": 0, "failed": 0, "playlists": 0}
    st.session_state.stats = stats

    task_id = f"web_{int(time.time())}"
    tracker = ProgressTracker(task_id)
    if not resume:
        tracker.clear()
    tracker.set_total(len(songs))

    # --- 搜索阶段 ---
    status_text = st.empty()
    progress_bar = st.progress(0, text="搜索中...")

    search_results = []
    for i, song in enumerate(songs):
        name = song["name"]
        artist = song.get("artist", "")
        album = song.get("album", "")

        if resume and tracker.is_searched(name, artist):
            result = tracker.get_search_result(name, artist)
        else:
            try:
                result = search_song(name, artist, album)
            except Exception as e:
                result = None
                log(f"搜索失败 [{name}]: {e}")
            tracker.mark_searched(name, artist, result)

        search_results.append({"input": song, "result": result})
        if result:
            stats["found"] += 1
        else:
            stats["not_found"] += 1

        progress = (i + 1) / len(songs)
        progress_bar.progress(progress, text=f"搜索中... {i + 1}/{len(songs)}")

    st.session_state.search_results = search_results
    progress_bar.progress(1.0, text="搜索完成")
    status_text.empty()

    log(f"搜索完成: 找到 {stats['found']} 首, 未找到 {stats['not_found']} 首")

    # --- 下载阶段 ---
    if do_download:
        to_download = [r for r in search_results if r["result"] is not None]
        if to_download:
            dl_bar = st.progress(0, text="下载中...")
            for i, r in enumerate(to_download):
                song_id = r["result"]["song_id"]
                category = r["input"].get("category", "")

                if resume and tracker.is_downloaded(song_id):
                    stats["downloaded"] += 1
                    dl_bar.progress((i + 1) / len(to_download), text=f"下载中... {i + 1}/{len(to_download)}")
                    continue

                try:
                    file_path = download_song(song_id, category=category)
                    if file_path:
                        tracker.mark_downloaded(song_id, file_path)
                        stats["downloaded"] += 1
                    else:
                        stats["failed"] += 1
                        log(f"下载失败 [{r['result']['name']}]: 无下载链接")
                except Exception as e:
                    stats["failed"] += 1
                    log(f"下载失败 [{r['result']['name']}]: {e}")

                dl_bar.progress((i + 1) / len(to_download), text=f"下载中... {i + 1}/{len(to_download)}")

            dl_bar.progress(1.0, text="下载完成")
            log(f"下载完成: 成功 {stats['downloaded']} 首, 失败 {stats['failed']} 首")

    # --- 创建歌单 ---
    if do_playlist:
        songs_by_category = defaultdict(list)
        for r in search_results:
            if r["result"] is None:
                continue
            category = r["input"].get("category", "") or DEFAULT_PLAYLIST_NAME
            songs_by_category[category].append(r["result"]["song_id"])

        if songs_by_category:
            log("正在创建歌单...")
            created = batch_create_playlists(songs_by_category, tracker=tracker)
            stats["playlists"] = len(created)
            for name, pid in created.items():
                log(f"歌单已创建: {name} (ID: {pid})")

    # --- 生成报告 ---
    report_data = []
    for r in search_results:
        inp = r["input"]
        res = r["result"]
        entry = {
            "input_name": inp["name"],
            "input_artist": inp.get("artist", ""),
            "category": inp.get("category", ""),
        }
        if res:
            entry["matched_name"] = res.get("name", "")
            entry["matched_artist"] = res.get("artist", "")
            entry["matched_album"] = res.get("album", "")
            song_id = res["song_id"]
            if tracker.is_downloaded(song_id):
                entry["status"] = "下载成功"
                entry["file_path"] = tracker.get_download_path(song_id) or ""
            elif not do_download:
                entry["status"] = "已匹配(未下载)"
            else:
                entry["status"] = "下载失败"
            entry["note"] = f"匹配度: {res.get('score', 0)}"
        else:
            entry.update({"matched_name": "", "matched_artist": "", "matched_album": "",
                          "status": "未找到", "file_path": "", "note": ""})
        report_data.append(entry)

    generate_report(report_data, REPORT_FILE)
    st.session_state.stats = stats
    st.session_state.running = False
    log("全部任务完成!")


# ---------- 辅助：打包下载文件夹为 zip ----------
def create_downloads_zip() -> bytes | None:
    downloads_dir = os.path.join(os.path.dirname(__file__), "downloads")
    if not os.path.exists(downloads_dir):
        return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(downloads_dir):
            for f in files:
                if f.endswith(".tmp"):
                    continue
                full = os.path.join(root, f)
                arcname = os.path.relpath(full, os.path.dirname(downloads_dir))
                zf.write(full, arcname)
    buf.seek(0)
    return buf.getvalue()


# ============================================================
#                        主界面
# ============================================================
def main():
    # 自动恢复登录
    try_restore_session()

    # ---------- 侧边栏 ----------
    with st.sidebar:
        st.markdown("### 账号")
        render_sidebar_user()

        st.divider()
        st.markdown("### 模板")
        template_path = os.path.join(os.path.dirname(__file__), "template", "song_list_template.xlsx")
        if not os.path.exists(template_path):
            generate_template()
        with open(template_path, "rb") as f:
            st.download_button(
                "📥  下载 Excel 模板",
                data=f.read(),
                file_name="song_list_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        st.divider()
        st.markdown("### 导出")
        report_path = os.path.join(os.path.dirname(__file__), REPORT_FILE)
        if os.path.exists(report_path):
            with open(report_path, "rb") as f:
                st.download_button(
                    "📊  下载结果报告",
                    data=f.read(),
                    file_name="result_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

        downloads_dir = os.path.join(os.path.dirname(__file__), "downloads")
        if os.path.exists(downloads_dir) and any(
            f for _, _, files in os.walk(downloads_dir) for f in files if not f.endswith(".tmp")
        ):
            if st.button("📦  打包下载歌曲 (ZIP)", use_container_width=True):
                with st.spinner("正在打包..."):
                    zip_data = create_downloads_zip()
                if zip_data:
                    st.download_button(
                        "⬇️  下载 ZIP",
                        data=zip_data,
                        file_name="downloads.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )

    # ---------- 主区域 ----------
    if not st.session_state.logged_in:
        render_login_page()
        return

    # 标题
    st.markdown("""
    <h1 style="font-weight: 800; font-size: 2rem; margin-bottom: 0;">
        🎵 网易云音乐批量下载
    </h1>
    <p style="color: #64748b; margin-top: 4px; margin-bottom: 2rem;">
        上传歌曲列表 → 搜索匹配 → 下载到本地 → 创建歌单
    </p>
    """, unsafe_allow_html=True)

    # 上传文件
    uploaded = st.file_uploader("上传歌曲列表文件", type=["xlsx", "csv"], help="支持 .xlsx 和 .csv 格式")

    if uploaded is None:
        st.info("请上传歌曲列表文件，或从左侧栏下载模板填写后上传")
        return

    # 保存上传文件
    tmp_path = os.path.join(os.path.dirname(__file__), f"_uploaded_{uploaded.name}")
    with open(tmp_path, "wb") as f:
        f.write(uploaded.getvalue())

    try:
        songs = read_song_list(tmp_path)
    except Exception as e:
        st.error(f"读取文件失败: {e}")
        return

    if not songs:
        st.warning("文件中没有有效的歌曲数据")
        return

    # 预览
    st.subheader(f"歌曲列表 ({len(songs)} 首)")
    import pandas as pd
    df = pd.DataFrame(songs)
    column_map = {"name": "歌曲名称", "artist": "歌手", "album": "专辑", "category": "分类/歌单", "note": "备注"}
    df = df.rename(columns=column_map)
    st.dataframe(df, use_container_width=True, height=min(400, 40 + 35 * len(songs)))

    # 选项
    st.subheader("执行选项")
    col1, col2, col3 = st.columns(3)
    with col1:
        do_download = st.checkbox("下载歌曲", value=True)
    with col2:
        do_playlist = st.checkbox("创建歌单", value=True)
    with col3:
        resume = st.checkbox("断点续传", value=False)

    # 执行
    if st.button("🚀 开始执行", type="primary", disabled=st.session_state.running, use_container_width=True):
        run_pipeline(songs, do_download, do_playlist, resume)

    # ---------- 结果展示 ----------
    stats = st.session_state.stats
    if stats["total"] > 0:
        st.subheader("执行结果")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("总歌曲", stats["total"])
        c2.metric("搜索到", stats["found"])
        c3.metric("未找到", stats["not_found"])
        c4.metric("已下载", stats["downloaded"])
        c5.metric("歌单数", stats["playlists"])

    if st.session_state.search_results:
        st.subheader("搜索匹配详情")
        rows = []
        for r in st.session_state.search_results:
            inp = r["input"]
            res = r["result"]
            if res:
                rows.append({
                    "歌曲名称": inp["name"],
                    "输入歌手": inp.get("artist", ""),
                    "匹配歌曲": res["name"],
                    "匹配歌手": res["artist"],
                    "匹配专辑": res["album"],
                    "匹配度": f"{res['score']:.1%}",
                    "状态": "✅ 匹配成功",
                })
            else:
                rows.append({
                    "歌曲名称": inp["name"],
                    "输入歌手": inp.get("artist", ""),
                    "匹配歌曲": "",
                    "匹配歌手": "",
                    "匹配专辑": "",
                    "匹配度": "",
                    "状态": "❌ 未找到",
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    if st.session_state.log_lines:
        with st.expander("执行日志", expanded=False):
            st.code("\n".join(st.session_state.log_lines))

    # 清理临时文件
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
