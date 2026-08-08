"""Streaming download of a single remote file with a progress bar."""
from __future__ import annotations

from pathlib import Path

import requests
from tqdm import tqdm


def download_stream(
    url: str,
    dest: Path,
    session: requests.Session,
    desc: str,
    headers: dict | None = None,
) -> None:
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
