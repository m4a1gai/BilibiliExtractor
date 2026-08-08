"""NetEase Cloud Music web QR-code login flow.

Mirrors the Bilibili flow: request a QR code (a key wrapped in a login
URL), render it in the terminal, then poll until the official app
confirms the scan and hand back the resulting session cookies.
"""
from __future__ import annotations

import time

import qrcode
import requests

from .api import UA
from .crypto import weapi

UNIKEY_URL = "https://music.163.com/weapi/login/qrcode/unikey"
POLL_URL = "https://music.163.com/weapi/login/qrcode/client/login"

EXPIRED = 800
WAITING = 801
SCANNED_NOT_CONFIRMED = 802
SUCCESS = 803


def qr_login(timeout: int = 180) -> dict:
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Referer": "https://music.163.com"})

    resp = session.post(UNIKEY_URL, data=weapi({"type": 1}), timeout=10).json()
    if resp.get("code") != 200:
        raise RuntimeError(f"获取二维码失败: {resp}")
    unikey = resp["unikey"]
    login_url = f"https://music.163.com/login?codekey={unikey}"

    qr = qrcode.QRCode(border=1)
    qr.add_data(login_url)
    qr.make()
    print("请使用网易云音乐手机客户端扫描下方二维码登录：")
    qr.print_ascii(invert=True)

    deadline = time.time() + timeout
    while time.time() < deadline:
        poll = session.post(
            POLL_URL, data=weapi({"type": 1, "key": unikey}), timeout=10
        ).json()
        code = poll.get("code")
        if code == SUCCESS:
            cookies = requests.utils.dict_from_cookiejar(session.cookies)
            print("登录成功。")
            return cookies
        if code == EXPIRED:
            raise RuntimeError("二维码已过期，请重新运行登录命令")
        if code == SCANNED_NOT_CONFIRMED:
            print("已扫描，请在手机上确认登录...")
        time.sleep(2)
    raise RuntimeError("登录超时")
