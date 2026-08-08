"""Embeds title/artist/album/cover-art tags into a downloaded audio file
so players like Apple Music show proper metadata after import."""
from __future__ import annotations

from pathlib import Path

import requests
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, ID3NoHeaderError, TALB, TIT2, TPE1
from mutagen.mp4 import MP4, MP4Cover

from .api import UA


def _fetch_cover(url: str) -> tuple[bytes, str] | None:
    if not url:
        return None
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    return resp.content, mime


def tag_file(path: Path, title: str, artist: str, album: str, cover_url: str) -> None:
    cover = _fetch_cover(cover_url)
    ext = path.suffix.lower()
    if ext == ".mp3":
        _tag_mp3(path, title, artist, album, cover)
    elif ext in (".m4a", ".mp4"):
        _tag_mp4(path, title, artist, album, cover)
    elif ext == ".flac":
        _tag_flac(path, title, artist, album, cover)
    # other/unrecognized formats: silently skip, download itself still succeeded


def _tag_mp3(path: Path, title: str, artist: str, album: str, cover: tuple[bytes, str] | None) -> None:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    tags["TIT2"] = TIT2(encoding=3, text=title)
    tags["TPE1"] = TPE1(encoding=3, text=artist)
    tags["TALB"] = TALB(encoding=3, text=album)
    if cover:
        data, mime = cover
        tags["APIC"] = APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data)
    tags.save(path)


def _tag_mp4(path: Path, title: str, artist: str, album: str, cover: tuple[bytes, str] | None) -> None:
    tags = MP4(path)
    tags["\xa9nam"] = [title]
    tags["\xa9ART"] = [artist]
    tags["\xa9alb"] = [album]
    if cover:
        data, mime = cover
        fmt = MP4Cover.FORMAT_PNG if "png" in mime else MP4Cover.FORMAT_JPEG
        tags["covr"] = [MP4Cover(data, imageformat=fmt)]
    tags.save()


def _tag_flac(path: Path, title: str, artist: str, album: str, cover: tuple[bytes, str] | None) -> None:
    tags = FLAC(path)
    tags["title"] = title
    tags["artist"] = artist
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
