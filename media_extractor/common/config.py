"""Cookie persistence for logged-in sessions, namespaced per platform."""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".media_extractor"


def cookie_file(platform: str) -> Path:
    return CONFIG_DIR / f"{platform}_cookies.json"


def load_cookies(platform: str) -> dict:
    path = cookie_file(platform)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_cookies(platform: str, cookies: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cookie_file(platform).write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def clear_cookies(platform: str) -> None:
    path = cookie_file(platform)
    if path.exists():
        path.unlink()
