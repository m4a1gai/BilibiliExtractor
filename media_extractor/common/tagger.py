"""Embeds title/artist/album/cover-art tags into a downloaded audio file
so players like Apple Music show proper metadata after import.

Fields left as None are simply not touched, so callers that only care
about e.g. cover art can omit the rest.
"""
from __future__ import annotations

from pathlib import Path

import requests
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TALB, TIT2, TPE1
from mutagen.mp4 import MP4, MP4Cover

Cover = tuple[bytes, str]  # (image bytes, mime type)


def fetch_cover(url: str, headers: dict | None = None) -> Cover | None:
    if not url:
        return None
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    return resp.content, mime


def embed_tags(
    path: Path,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    cover: Cover | None = None,
) -> None:
    ext = path.suffix.lower()
    if ext == ".mp3":
        _tag_mp3(path, title, artist, album, cover)
    elif ext in (".m4a", ".mp4"):
        _tag_mp4(path, title, artist, album, cover)
    elif ext == ".flac":
        _tag_flac(path, title, artist, album, cover)
    # other/unrecognized formats: silently skip, download itself still succeeded


def _tag_mp3(path: Path, title, artist, album, cover: Cover | None) -> None:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    if title is not None:
        tags["TIT2"] = TIT2(encoding=3, text=title)
    if artist is not None:
        tags["TPE1"] = TPE1(encoding=3, text=artist)
    if album is not None:
        tags["TALB"] = TALB(encoding=3, text=album)
    if cover:
        data, mime = cover
        tags["APIC"] = APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data)
    tags.save(path)


def _tag_mp4(path: Path, title, artist, album, cover: Cover | None) -> None:
    tags = MP4(path)
    if title is not None:
        tags["\xa9nam"] = [title]
    if artist is not None:
        tags["\xa9ART"] = [artist]
    if album is not None:
        tags["\xa9alb"] = [album]
    if cover:
        data, mime = cover
        fmt = MP4Cover.FORMAT_PNG if "png" in mime else MP4Cover.FORMAT_JPEG
        tags["covr"] = [MP4Cover(data, imageformat=fmt)]
    tags.save()


def _tag_flac(path: Path, title, artist, album, cover: Cover | None) -> None:
    tags = FLAC(path)
    if title is not None:
        tags["title"] = title
    if artist is not None:
        tags["artist"] = artist
    if album is not None:
        tags["album"] = album
    if cover:
        data, mime = cover
        pic = Picture()
        pic.type = 3
        pic.mime = mime
        pic.data = data
        tags.clear_pictures()
        tags.add_picture(pic)
    tags.save()
