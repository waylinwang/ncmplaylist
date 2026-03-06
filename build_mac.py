"""PyInstaller 打包脚本 - macOS"""

import subprocess
import sys
import os
import glob
import shutil
import streamlit
import pyncm

# 获取关键路径
streamlit_dir = os.path.dirname(streamlit.__file__)
pyncm_dir = os.path.dirname(pyncm.__file__)
base_dir = os.path.dirname(os.path.abspath(__file__))
site_packages = os.path.dirname(streamlit_dir)

# 需要打包的数据文件
datas = [
    (os.path.join(base_dir, "app.py"), "."),
    (os.path.join(base_dir, "config.py"), "."),
    (os.path.join(base_dir, "auth.py"), "."),
    (os.path.join(base_dir, "search.py"), "."),
    (os.path.join(base_dir, "downloader.py"), "."),
    (os.path.join(base_dir, "playlist_manager.py"), "."),
    (os.path.join(base_dir, "progress_tracker.py"), "."),
    (os.path.join(base_dir, "excel_handler.py"), "."),
    (os.path.join(base_dir, "utils.py"), "."),
    (os.path.join(base_dir, "template"), "template"),
    # Streamlit 需要其静态文件
    (os.path.join(streamlit_dir, "static"), os.path.join("streamlit", "static")),
    (os.path.join(streamlit_dir, "runtime"), os.path.join("streamlit", "runtime")),
    # pyncm 包
    (pyncm_dir, "pyncm"),
]

# 收集所有 dist-info 目录（解决 importlib.metadata.PackageNotFoundError）
for dist_info in glob.glob(os.path.join(site_packages, "*.dist-info")):
    dirname = os.path.basename(dist_info)
    datas.append((dist_info, dirname))

# 隐藏导入
hidden_imports = [
    "streamlit",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "pyncm",
    "pyncm.apis",
    "pyncm.apis.login",
    "pyncm.apis.cloudsearch",
    "pyncm.apis.track",
    "pyncm.apis.playlist",
    "openpyxl",
    "qrcode",
    "mutagen",
    "mutagen.mp3",
    "mutagen.id3",
    "PIL",
    "tqdm",
    "pandas",
    "pyarrow",
    "altair",
    "jinja2",
    "toml",
    "click",
    "packaging",
    "watchdog",
]

# 构建 PyInstaller 命令
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--name", "neteasymusic",
    "--onedir",
    "--windowed",
    "--noconfirm",
    "--clean",
    "--icon", os.path.join(base_dir, "icon.icns"),
]

# 添加数据文件
for src, dst in datas:
    if os.path.exists(src):
        cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

# 添加隐藏导入
for imp in hidden_imports:
    cmd.extend(["--hidden-import", imp])

# 入口文件
cmd.append("launcher.py")

print("开始打包...")
print(f"命令: {' '.join(cmd[:10])}... (共 {len(cmd)} 个参数)")
print()

result = subprocess.run(cmd, cwd=base_dir)

if result.returncode != 0:
    print("\n打包失败，请检查错误信息")
    sys.exit(1)

# ── 签名：移除隔离属性 + ad-hoc 签名 ──
app_path = os.path.join(base_dir, "dist", "neteasymusic.app")
print("\n签名中...")

# 移除所有文件的隔离属性
subprocess.run(["xattr", "-cr", app_path])

# 对所有 dylib / so / 可执行文件进行 ad-hoc 签名
import pathlib
sign_exts = {".dylib", ".so", ".bundle"}
app_contents = pathlib.Path(app_path)

# 先签名所有动态库
for f in sorted(app_contents.rglob("*")):
    if f.is_file() and f.suffix in sign_exts:
        subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", str(f)],
            capture_output=True
        )

# 再签名主可执行文件
macos_dir = app_contents / "Contents" / "MacOS"
for f in macos_dir.iterdir():
    if f.is_file():
        subprocess.run(
            ["codesign", "--force", "--sign", "-", str(f)],
            capture_output=True
        )

# 最后签名整个 .app
subprocess.run(["codesign", "--force", "--deep", "--sign", "-", app_path])

print("签名完成!")

print("\n" + "=" * 50)
print("打包成功!")
print(f"输出: {app_path}")
print("=" * 50)
print("\n其他 Mac 首次打开如遇安全提示，运行:")
print(f'  sudo xattr -cr "{app_path}"')
