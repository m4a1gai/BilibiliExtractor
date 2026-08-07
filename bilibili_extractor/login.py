"""Bilibili web QR-code login flow.

1. Ask Bilibili for a QR code (a URL + key).
2. Render it in the terminal for the user to scan with the official app.
3. Poll until the app confirms the scan, then harvest the session cookies.
"""
from __future__ import annotations

import time

import qrcode
import requests

from .api import UA

GENERATE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"

# poll status codes documented by the community (bilibili-API-collect)
NOT_SCANNED = 86101
SCANNED_NOT_CONFIRMED = 86090
EXPIRED = 86038
SUCCESS = 0


def qr_login(timeout: int = 180) -> dict:
    """Runs the interactive QR login flow, returns the resulting cookie dict."""
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    resp = session.get(GENERATE_URL, timeout=10).json()
    if resp.get("code") != 0:
        raise RuntimeError(f"获取二维码失败: {resp.get('message')}")
    url = resp["data"]["url"]
    qrcode_key = resp["data"]["qrcode_key"]

    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make()
    print("请使用 Bilibili 手机客户端扫描下方二维码登录：")
    qr.print_ascii(invert=True)

    deadline = time.time() + timeout
    while time.time() < deadline:
        poll = session.get(
            POLL_URL, params={"qrcode_key": qrcode_key}, timeout=10
        ).json()
        data = poll.get("data", {})
        code = data.get("code")
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
