"""Streaming download of a single DASH stream with a progress bar."""
from __future__ import annotations

from pathlib import Path

import requests
from tqdm import tqdm

from .api import UA


def download_stream(url: str, referer: str, dest: Path, session: requests.Session, desc: str) -> None:
    headers = {"User-Agent": UA, "Referer": referer}
    with session.get(url, headers=headers, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f, tqdm(
            total=total or None, unit="B", unit_scale=True, desc=desc
        ) as bar:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
