"""登录 / 会话管理：二维码扫码登录，session 持久化"""

import os
import json
import time
from pyncm import GetCurrentSession, SetCurrentSession, LoadSessionFromString, DumpSessionAsString
from pyncm.apis.login import (
    LoginQrcodeUnikey,
    LoginQrcodeCheck,
    GetCurrentLoginStatus,
    GetLoginQRCodeUrl,
)
from config import SESSION_FILE


def _session_path() -> str:
    return os.path.join(os.path.dirname(__file__), SESSION_FILE)


def _get_profile() -> dict | None:
    """获取当前登录用户 profile"""
    try:
        status = GetCurrentLoginStatus()
        # 尝试多种可能的返回结构
        profile = status.get("profile")
        if not profile:
            profile = status.get("content", {}).get("profile")
        if not profile:
            profile = status.get("account")
        return profile
    except Exception:
        return None


def _print_user_info():
    """打印当前登录用户信息"""
    profile = _get_profile()
    if profile:
        nickname = profile.get("nickname", "未知用户")
        vip_type = profile.get("vipType", 0)
        print(f"用户: {nickname}")
        print(f"VIP 状态: {'VIP' if vip_type > 0 else '非VIP'}")
    else:
        print("用户信息获取失败（登录可能仍然有效）")


def save_session():
    """保存当前会话到文件"""
    session = GetCurrentSession()
    session_str = DumpSessionAsString(session)
    with open(_session_path(), "w", encoding="utf-8") as f:
        f.write(session_str)


def load_session() -> bool:
    """从文件加载会话，返回是否成功"""
    path = _session_path()
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            session_str = f.read()
        session = LoadSessionFromString(session_str)
        SetCurrentSession(session)
        # 验证会话是否有效
        profile = _get_profile()
        if profile:
            print(f"已从缓存恢复登录: {profile.get('nickname', '未知用户')}")
            return True
        return False
    except Exception:
        return False


def check_login() -> bool:
    """检查当前是否已登录"""
    return _get_profile() is not None


def qrcode_login() -> bool:
    """二维码扫码登录流程"""
    print("正在生成登录二维码...")

    # 获取二维码 key
    uuid_result = LoginQrcodeUnikey()
    uuid = uuid_result.get("unikey")
    if not uuid:
        print("获取二维码失败")
        return False

    # 生成二维码 URL
    qr_url = GetLoginQRCodeUrl(uuid)

    # 尝试在终端显示二维码
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        print(f"请安装 qrcode 库以显示二维码，或手动访问: {qr_url}")

    print("\n请使用网易云音乐 App 扫描上方二维码登录")
    print("等待扫码中", end="", flush=True)

    # 轮询检查扫码状态
    max_wait = 120  # 最多等待 120 秒
    start_time = time.time()

    while time.time() - start_time < max_wait:
        time.sleep(2)
        print(".", end="", flush=True)

        try:
            check_result = LoginQrcodeCheck(uuid)
            code = check_result.get("code", 0)

            if code == 803:
                # 登录成功
                print("\n登录成功!")
                _print_user_info()
                try:
                    save_session()
                    print("会话已缓存")
                except Exception as e:
                    print(f"会话缓存失败（不影响本次登录）: {e}")
                return True
            elif code == 800:
                print("\n二维码已过期，请重试")
                return False
            # 801 = 等待扫码, 802 = 已扫码待确认
        except Exception:
            pass

    print("\n登录超时，请重试")
    return False


def ensure_login() -> bool:
    """确保已登录：先尝试加载缓存，失败则扫码登录"""
    if load_session():
        return True
    print("未找到有效的登录会话，需要扫码登录")
    return qrcode_login()
