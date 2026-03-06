"""Streamlit Web 界面 - 网易云音乐批量下载工具"""

import os
import io
import time
import base64
import zipfile
from collections import defaultdict

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import qrcode
from PIL import Image

from pyncm.apis.login import LoginQrcodeUnikey, LoginQrcodeCheck, GetLoginQRCodeUrl

from auth import load_session, save_session, _get_profile
from excel_handler import generate_template, read_song_list, generate_report
from search import search_song
from downloader import download_song
from playlist_manager import batch_create_playlists
from progress_tracker import ProgressTracker
from config import DEFAULT_PLAYLIST_NAME, REPORT_FILE, get_data_dir, get_app_dir

# ── 页面配置 ──
st.set_page_config(page_title="NCM 批量下载", page_icon="🎵", layout="wide",
                   initial_sidebar_state="expanded")

# ── 莫兰迪配色全局样式 ──
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');

:root {
    --morandi-bg:      #f5f0eb;
    --morandi-card:    #ebe5de;
    --morandi-rose:    #c4a4a0;
    --morandi-sage:    #a3b5a6;
    --morandi-stone:   #b5b0a8;
    --morandi-dusk:    #9b8e9e;
    --morandi-clay:    #c9b8a8;
    --morandi-ink:     #4a4541;
    --morandi-muted:   #8a8279;
    --morandi-light:   #f9f6f2;
    --morandi-border:  #ddd6cc;
    --morandi-accent:  #b07d6a;
}

/* 基础 */
html, body, [class*="css"] {
    font-family: 'Noto Sans SC', -apple-system, sans-serif;
}
#MainMenu, footer { visibility: hidden; }
/* 隐藏顶部装饰条但保留侧边栏切换按钮 */
header[data-testid="stHeader"] {
    background: transparent !important;
    backdrop-filter: none !important;
}
header[data-testid="stHeader"] .stDeployButton,
header[data-testid="stHeader"] #MainMenu {
    display: none !important;
}

/* 主区域背景 */
.stApp, .main .block-container {
    background-color: var(--morandi-bg) !important;
}

/* ── 侧边栏 ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #4a4541, #3d3935, #332f2b) !important;
    border-right: none !important;
}
section[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
    padding-top: 1.5rem;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span {
    color: rgba(255,255,255,0.65) !important;
}
section[data-testid="stSidebar"] label {
    color: rgba(255,255,255,0.7) !important;
}
section[data-testid="stSidebar"] .stCaption {
    color: rgba(255,255,255,0.4) !important;
}

/* 侧边栏标题 */
.sidebar-label {
    font-family: 'Cormorant Garamond', serif;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: rgba(255,255,255,0.35) !important;
    padding-bottom: 8px;
    margin-bottom: 4px;
}

/* 侧边栏分割线 */
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.06) !important;
}

/* 侧边栏按钮 */
section[data-testid="stSidebar"] button[kind="secondary"] {
    background: rgba(255,255,255,0.06) !important;
    color: rgba(255,255,255,0.75) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 6px !important;
    font-weight: 400 !important;
    font-size: 0.82rem !important;
    transition: all 0.2s ease !important;
}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.1) !important;
    border-color: rgba(255,255,255,0.15) !important;
}

/* 用户卡片 */
.user-card {
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 14px;
    display: flex;
    align-items: center;
    gap: 12px;
    border: 1px solid rgba(255,255,255,0.06);
}
.user-avatar {
    width: 40px; height: 40px; border-radius: 50%;
    background: linear-gradient(135deg, var(--morandi-rose), var(--morandi-accent));
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 600; font-size: 0.95rem; flex-shrink: 0;
    letter-spacing: 0.5px;
}
.user-name {
    color: rgba(255,255,255,0.9);
    font-weight: 500;
    font-size: 0.88rem;
}
.vip-tag {
    font-size: 0.58rem; font-weight: 600; padding: 2px 8px; border-radius: 3px;
    display: inline-block; margin-top: 3px; letter-spacing: 1px;
    text-transform: uppercase;
}
.vip-tag.vip {
    background: linear-gradient(135deg, var(--morandi-clay), var(--morandi-accent));
    color: #fff;
}
.vip-tag.free {
    background: rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.4);
}

/* ── 主内容区 ── */
.page-header {
    margin-bottom: 1.8rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--morandi-border);
}
.page-header h2 {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2rem;
    font-weight: 600;
    color: var(--morandi-ink);
    margin: 0 0 4px 0;
    letter-spacing: 1px;
}
.page-header p {
    color: var(--morandi-muted);
    font-size: 0.85rem;
    margin: 0;
    font-weight: 300;
    letter-spacing: 0.5px;
}

/* 指标卡片 */
div[data-testid="stMetric"] {
    background: var(--morandi-light);
    border-radius: 10px;
    padding: 18px 20px;
    border: 1px solid var(--morandi-border);
}
div[data-testid="stMetric"] label {
    color: var(--morandi-muted) !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--morandi-ink) !important;
    font-family: 'Cormorant Garamond', serif !important;
    font-weight: 600 !important;
    font-size: 1.8rem !important;
}

/* 主按钮 */
button[kind="primary"] {
    background: linear-gradient(135deg, var(--morandi-accent), #a06b58) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    letter-spacing: 0.8px !important;
    transition: all 0.25s ease !important;
    padding: 0.6rem 1.5rem !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #a06b58, #8f5d4c) !important;
    box-shadow: 0 6px 20px rgba(176,125,106,0.25) !important;
    transform: translateY(-1px);
}

/* 文件上传区 */
section[data-testid="stFileUploader"] {
    background: var(--morandi-light) !important;
    border: 2px dashed var(--morandi-border) !important;
    border-radius: 10px !important;
}
section[data-testid="stFileUploader"]:hover {
    border-color: var(--morandi-rose) !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.3px !important;
}

/* Expander */
details {
    background: var(--morandi-light) !important;
    border: 1px solid var(--morandi-border) !important;
    border-radius: 10px !important;
}

/* Toggle */
div[data-testid="stToggle"] label span {
    color: var(--morandi-ink) !important;
    font-weight: 400 !important;
}

/* Selectbox */
div[data-baseweb="select"] > div {
    background: var(--morandi-light) !important;
    border-color: var(--morandi-border) !important;
}

/* Section subtitle */
.section-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--morandi-ink);
    letter-spacing: 0.5px;
    margin-bottom: 12px;
}

/* Status */
details[data-testid="stStatusWidget"] {
    border-color: var(--morandi-border) !important;
}

/* Info / Warning boxes */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
}
</style>""", unsafe_allow_html=True)


# ── 状态初始化 ──
_DEFAULTS = {
    "logged_in": False, "username": "", "vip": False,
    "qr_uuid": None, "qr_b64": None, "scan_status": "waiting",
    "songs": None, "running": False,
    "log_lines": [], "search_results": [],
    "stats": {"total": 0, "found": 0, "not_found": 0, "downloaded": 0, "failed": 0, "playlists": 0},
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── 工具函数 ──
def log(msg: str):
    st.session_state.log_lines.append(msg)


def _qr_to_b64(url: str) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#4a4541", back_color="#f5f0eb").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _zip_downloads() -> bytes | None:
    d = os.path.join(get_data_dir(), "downloads")
    if not os.path.isdir(d):
        return None
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(".tmp"):
                    continue
                full = os.path.join(root, f)
                zf.write(full, os.path.relpath(full, os.path.dirname(d)))
                count += 1
    if count == 0:
        return None
    buf.seek(0)
    return buf.getvalue()


def _reset_login():
    for k in ("logged_in", "username", "vip", "qr_uuid", "qr_b64", "scan_status"):
        st.session_state[k] = _DEFAULTS[k]
    p = os.path.join(get_data_dir(), ".session_cache")
    if os.path.exists(p):
        os.remove(p)


# ── 登录恢复 ──
def _try_restore():
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


# ── 侧边栏 ──
def _sidebar():
    with st.sidebar:
        st.markdown('<div class="sidebar-label">Account</div>', unsafe_allow_html=True)
        if st.session_state.logged_in:
            u = st.session_state.username
            vip = "vip" if st.session_state.vip else "free"
            label = "VIP" if st.session_state.vip else "FREE"
            st.markdown(f"""<div class="user-card">
                <div class="user-avatar">{u[0] if u else '?'}</div>
                <div><div class="user-name">{u}</div>
                <span class="vip-tag {vip}">{label}</span></div>
            </div>""", unsafe_allow_html=True)
            st.markdown("")
            if st.button("切换账号", use_container_width=True):
                _reset_login()
                st.rerun()
        else:
            st.caption("未登录")

        st.divider()
        st.markdown('<div class="sidebar-label">Tools</div>', unsafe_allow_html=True)
        tpl = os.path.join(get_app_dir(), "template", "song_list_template.xlsx")
        if not os.path.exists(tpl):
            generate_template()
        with open(tpl, "rb") as f:
            st.download_button("Excel 模板", f.read(),
                               file_name="song_list_template.xlsx", use_container_width=True)

        rpt = os.path.join(get_data_dir(), REPORT_FILE)
        if os.path.exists(rpt):
            with open(rpt, "rb") as f:
                st.download_button("结果报告", f.read(),
                                   file_name="result_report.xlsx", use_container_width=True)

        zdata = _zip_downloads()
        if zdata:
            st.download_button("全部歌曲 (ZIP)", zdata,
                               file_name="downloads.zip", mime="application/zip",
                               use_container_width=True)

        st.divider()
        st.markdown('<div class="sidebar-label">Info</div>', unsafe_allow_html=True)
        st.caption("NCM Batch Downloader")
        st.caption("v1.0")


# ── 登录页 ──
def _login_page():
    if not st.session_state.qr_uuid:
        r = LoginQrcodeUnikey()
        uid = r.get("unikey")
        if uid:
            st.session_state.qr_uuid = uid
            st.session_state.qr_b64 = _qr_to_b64(GetLoginQRCodeUrl(uid))
            st.session_state.scan_status = "waiting"
        else:
            st.error("获取二维码失败，请刷新页面")
            return

    b64 = st.session_state.qr_b64
    status = st.session_state.scan_status

    badge_map = {
        "waiting":  ("等待扫码", "#8a8279", "#ebe5de", "#ddd6cc"),
        "scanned":  ("已扫码 - 请在手机确认后点击下方按钮", "#6b8f71", "#e8f0e9", "#c5d8c7"),
        "expired":  ("二维码已过期", "#b07d6a", "#f3ebe5", "#dcc8bb"),
    }
    txt, color, bg, bd = badge_map.get(status, badge_map["waiting"])

    steps_data = [
        ("1", "打开网易云音乐 App", status in ("scanned",)),
        ("2", "扫描上方二维码",      status in ("scanned",)),
        ("3", "在手机上确认登录",     False),
    ]

    steps_html = ""
    for num, label, done in steps_data:
        cls = "done" if done else ("active" if num == "1" and status == "waiting" else "")
        dot = "&#10003;" if done else num
        steps_html += f'<div class="s {cls}"><div class="d">{dot}</div>{label}</div>'

    card = f"""<html><head><meta charset="utf-8"><style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;600&display=swap');
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Noto Sans SC',sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;background:transparent}}
    .c{{background:#f9f6f2;border-radius:16px;padding:2.5rem 2.8rem;max-width:380px;width:100%;text-align:center;
        border:1px solid #ddd6cc;box-shadow:0 8px 40px rgba(74,69,65,.08)}}
    .brand{{font-family:'Cormorant Garamond',serif;font-size:.7rem;font-weight:600;color:#b5b0a8;
        letter-spacing:3px;text-transform:uppercase;margin-bottom:6px}}
    .t{{font-family:'Cormorant Garamond',serif;font-size:1.6rem;font-weight:600;color:#4a4541;margin-bottom:1.4rem;letter-spacing:1px}}
    .t em{{font-style:normal;color:#b07d6a}}
    .q{{background:#fff;border-radius:12px;padding:14px;display:inline-block;margin-bottom:1rem;
        border:1px solid #ebe5de;box-shadow:0 2px 12px rgba(74,69,65,.06)}}
    .q img{{display:block;width:180px;height:180px}}
    .badge{{display:inline-block;padding:6px 18px;border-radius:50px;font-size:.72rem;font-weight:500;margin-bottom:1.3rem;
        color:{color};background:{bg};border:1px solid {bd};letter-spacing:0.3px}}
    .steps{{display:flex;flex-direction:column;gap:9px;text-align:left;padding:0 8px}}
    .s{{display:flex;align-items:center;gap:10px;color:#b5b0a8;font-size:.78rem;font-weight:400}}
    .s.active{{color:#4a4541;font-weight:500}}.s.done{{color:#6b8f71;font-weight:500}}
    .d{{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
        font-size:.68rem;font-weight:600;flex-shrink:0;
        background:#ebe5de;border:1.5px solid #ddd6cc;color:#b5b0a8}}
    .s.active .d{{background:#f3ebe5;border-color:#b07d6a;color:#b07d6a}}
    .s.done .d{{background:#e8f0e9;border-color:#6b8f71;color:#6b8f71}}
    </style></head><body>
    <div class="c">
        <div class="brand">NetEase Cloud Music</div>
        <div class="t">扫码<em>登录</em></div>
        <div class="q"><img src="data:image/png;base64,{b64}"/></div>
        <div class="badge">{txt}</div>
        <div class="steps">{steps_html}</div>
    </div></body></html>"""

    components.html(card, height=510)

    # ── 按钮 ──
    _l, center, _r = st.columns([1.2, 2, 1.2])
    with center:
        if status == "expired":
            if st.button("刷新二维码", use_container_width=True, type="primary"):
                st.session_state.qr_uuid = None
                st.rerun()
        else:
            if st.button("我已扫码，确认登录", use_container_width=True, type="primary"):
                with st.spinner("正在验证..."):
                    try:
                        code = LoginQrcodeCheck(st.session_state.qr_uuid).get("code", 0)
                    except Exception:
                        code = 0
                if code == 803:
                    try:
                        save_session()
                    except Exception:
                        pass
                    profile = _get_profile()
                    st.session_state.logged_in = True
                    st.session_state.username = profile.get("nickname", "未知用户") if profile else "未知用户"
                    st.session_state.vip = (profile.get("vipType", 0) > 0) if profile else False
                    st.session_state.qr_uuid = None
                    st.toast("登录成功!")
                    time.sleep(0.5)
                    st.rerun()
                elif code == 800:
                    st.session_state.scan_status = "expired"
                    st.rerun()
                elif code == 802:
                    st.session_state.scan_status = "scanned"
                    st.toast("已扫码，请在手机确认后再次点击按钮")
                    st.rerun()
                else:
                    st.toast("尚未扫码，请先用网易云 App 扫描二维码")

            if st.button("刷新二维码", use_container_width=True):
                st.session_state.qr_uuid = None
                st.rerun()


# ── 执行流程 ──
def _run(songs, do_dl, do_pl, resume, bitrate=320000):
    st.session_state.running = True
    st.session_state.log_lines = []
    st.session_state.search_results = []
    stats = {"total": len(songs), "found": 0, "not_found": 0, "downloaded": 0, "failed": 0, "playlists": 0}

    tid = f"web_{int(time.time())}"
    tracker = ProgressTracker(tid)
    if not resume:
        tracker.clear()
    tracker.set_total(len(songs))

    # ── 搜索 ──
    with st.status("搜索歌曲...", expanded=True) as s:
        bar = st.progress(0)
        results = []
        for i, song in enumerate(songs):
            name, artist, album = song["name"], song.get("artist", ""), song.get("album", "")
            if resume and tracker.is_searched(name, artist):
                r = tracker.get_search_result(name, artist)
            else:
                try:
                    r = search_song(name, artist, album)
                except Exception as e:
                    r = None
                    log(f"搜索失败 [{name}]: {e}")
                tracker.mark_searched(name, artist, r)

            results.append({"input": song, "result": r})
            stats["found" if r else "not_found"] += 1
            bar.progress((i + 1) / len(songs), text=f"{i+1} / {len(songs)}")

        s.update(label=f"搜索完成 - 找到 {stats['found']} 首，未找到 {stats['not_found']} 首", state="complete")
    log(f"搜索完成: 找到 {stats['found']} / 未找到 {stats['not_found']}")

    # ── 下载 ──
    if do_dl:
        to_dl = [r for r in results if r["result"]]
        if to_dl:
            with st.status(f"下载歌曲 (0/{len(to_dl)})...", expanded=True) as s:
                bar = st.progress(0)
                for i, r in enumerate(to_dl):
                    sid = r["result"]["song_id"]
                    cat = r["input"].get("category", "")
                    if resume and tracker.is_downloaded(sid):
                        stats["downloaded"] += 1
                    else:
                        try:
                            fp = download_song(sid, category=cat, bitrate=bitrate)
                            if fp:
                                tracker.mark_downloaded(sid, fp)
                                stats["downloaded"] += 1
                            else:
                                stats["failed"] += 1
                                log(f"下载失败 [{r['result']['name']}]: 无链接")
                        except Exception as e:
                            stats["failed"] += 1
                            log(f"下载失败 [{r['result']['name']}]: {e}")
                    bar.progress((i + 1) / len(to_dl), text=f"{i+1} / {len(to_dl)}")
                    s.update(label=f"下载歌曲 ({i+1}/{len(to_dl)})...")
                s.update(label=f"下载完成 - 成功 {stats['downloaded']}，失败 {stats['failed']}", state="complete")
            log(f"下载完成: 成功 {stats['downloaded']} / 失败 {stats['failed']}")

    # ── 创建歌单 ──
    if do_pl:
        by_cat = defaultdict(list)
        for r in results:
            if r["result"]:
                by_cat[r["input"].get("category", "") or DEFAULT_PLAYLIST_NAME].append(r["result"]["song_id"])
        if by_cat:
            with st.status("创建歌单...", expanded=True) as s:
                created = batch_create_playlists(by_cat, tracker=tracker)
                stats["playlists"] = len(created)
                for n, pid in created.items():
                    log(f"歌单: {n} (ID: {pid})")
                s.update(label=f"歌单创建完成 - {len(created)} 个", state="complete")

    # ── 生成报告 ──
    report_data = []
    for r in results:
        inp, res = r["input"], r["result"]
        e = {"input_name": inp["name"], "input_artist": inp.get("artist", ""), "category": inp.get("category", "")}
        if res:
            e.update(matched_name=res["name"], matched_artist=res["artist"], matched_album=res["album"],
                     note=f"匹配度: {res.get('score', 0)}")
            sid = res["song_id"]
            e["status"] = "下载成功" if tracker.is_downloaded(sid) else ("已匹配(未下载)" if not do_dl else "下载失败")
            e["file_path"] = tracker.get_download_path(sid) or ""
        else:
            e.update(matched_name="", matched_artist="", matched_album="",
                     status="未找到", file_path="", note="")
        report_data.append(e)
    generate_report(report_data, os.path.join(get_data_dir(), REPORT_FILE))

    st.session_state.search_results = results
    st.session_state.stats = stats
    st.session_state.running = False
    st.toast("全部任务完成!")
    log("全部任务完成!")


# ── 结果展示 ──
def _show_results():
    stats = st.session_state.stats
    if stats["total"] == 0:
        return

    st.markdown("---")
    st.markdown('<div class="section-title">执行结果</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("总歌曲", stats["total"])
    c2.metric("搜索到", stats["found"])
    c3.metric("未找到", stats["not_found"])
    c4.metric("已下载", stats["downloaded"])
    c5.metric("歌单数", stats["playlists"])

    if not st.session_state.search_results:
        return

    found, missed = [], []
    for r in st.session_state.search_results:
        inp, res = r["input"], r["result"]
        if res:
            found.append({"歌曲": inp["name"], "输入歌手": inp.get("artist", ""),
                          "匹配歌曲": res["name"], "匹配歌手": res["artist"],
                          "专辑": res["album"], "匹配度": f"{res['score']:.0%}"})
        else:
            missed.append({"歌曲": inp["name"], "歌手": inp.get("artist", ""),
                           "分类": inp.get("category", "")})

    tab1, tab2, tab3 = st.tabs([
        f"匹配成功 ({len(found)})",
        f"未找到 ({len(missed)})",
        f"日志 ({len(st.session_state.log_lines)})",
    ])
    with tab1:
        if found:
            st.dataframe(pd.DataFrame(found), use_container_width=True, hide_index=True)
        else:
            st.info("没有匹配成功的歌曲")
    with tab2:
        if missed:
            st.dataframe(pd.DataFrame(missed), use_container_width=True, hide_index=True)
        else:
            st.success("全部匹配成功!")
    with tab3:
        if st.session_state.log_lines:
            st.code("\n".join(st.session_state.log_lines), language=None)
        else:
            st.info("暂无日志")


# ══════════════════════════════════════
#               主入口
# ══════════════════════════════════════
def main():
    _try_restore()
    _sidebar()

    if not st.session_state.logged_in:
        _login_page()
        return

    # ── 标题 ──
    st.markdown("""<div class="page-header">
        <h2>网易云音乐批量下载</h2>
        <p>上传歌曲列表 &rarr; 搜索匹配 &rarr; 下载 &rarr; 创建歌单</p>
    </div>""", unsafe_allow_html=True)

    # ── Step 1: 上传 ──
    uploaded = st.file_uploader("上传歌曲列表", type=["xlsx", "csv"],
                                help="支持 .xlsx / .csv，可从左侧下载模板")
    if not uploaded:
        st.info("上传歌曲列表文件开始使用，或从左侧栏下载 Excel 模板")
        _show_results()
        return

    # 缓存解析结果
    file_key = f"{uploaded.name}_{uploaded.size}"
    if st.session_state.get("_file_key") != file_key:
        tmp = os.path.join(get_data_dir(), f"_tmp_{uploaded.name}")
        with open(tmp, "wb") as f:
            f.write(uploaded.getvalue())
        try:
            st.session_state.songs = read_song_list(tmp)
            st.session_state["_file_key"] = file_key
        except Exception as e:
            st.error(f"读取失败: {e}")
            return
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    songs = st.session_state.songs
    if not songs:
        st.warning("文件中没有有效数据")
        return

    # ── Step 2: 预览 ──
    with st.expander(f"歌曲列表预览 ({len(songs)} 首)", expanded=False):
        df = pd.DataFrame(songs).rename(columns={
            "name": "歌曲名称", "artist": "歌手", "album": "专辑",
            "category": "分类/歌单", "note": "备注"})
        st.dataframe(df, use_container_width=True, hide_index=True,
                     height=min(400, 38 + 35 * len(songs)))

    # ── Step 3: 配置 + 执行 ──
    st.markdown('<div class="section-title">执行配置</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    do_dl = col1.toggle("下载歌曲", value=True)
    do_pl = col2.toggle("创建歌单", value=True)
    resume = col3.toggle("断点续传", value=False)
    quality_options = {"标准 128kbps": 128000, "高品 192kbps": 192000, "极高 320kbps": 320000, "无损 FLAC": 999000}
    quality = col4.selectbox("音质", list(quality_options.keys()), index=2, disabled=not do_dl)

    bitrate = quality_options[quality]

    st.markdown("")
    if st.button("开始执行", type="primary", use_container_width=True,
                 disabled=st.session_state.running):
        _run(songs, do_dl, do_pl, resume, bitrate=bitrate)

    # ── Step 4: 结果 ──
    _show_results()


if __name__ == "__main__":
    main()
