"""Cookie persistence for logged-in sessions."""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".bilibili_extractor"
COOKIE_FILE = CONFIG_DIR / "cookies.json"


def load_cookies() -> dict:
    if not COOKIE_FILE.exists():
        return {}
    try:
        return json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_cookies(cookies: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_cookies() -> None:
    if COOKIE_FILE.exists():
        COOKIE_FILE.unlink()
