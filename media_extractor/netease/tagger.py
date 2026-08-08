"""NetEase-specific wrapper around the shared audio tagger."""
from __future__ import annotations

from pathlib import Path

from ..common.tagger import embed_tags, fetch_cover
from .api import UA


def tag_file(path: Path, title: str, artist: str, album: str, cover_url: str) -> None:
    cover = fetch_cover(cover_url, headers={"User-Agent": UA})
    embed_tags(path, title=title, artist=artist, album=album, cover=cover)
