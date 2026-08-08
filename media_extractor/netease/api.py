"""Thin client around NetEase Cloud Music's web (weapi) endpoints used to
resolve a song/playlist id into a playable download URL."""
from __future__ import annotations

import json

import requests

from .crypto import weapi

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Highest-to-lowest; only ever resolves beyond "exhigher" when the account
# is a VIP entitled to lossless/Hi-Res/master-tape tracks.
QUALITY_CASCADE = ["jymaster", "sky", "jyeffect", "hires", "lossless", "exhigher", "higher", "standard"]

QUALITY_NAMES = {
    "jymaster": "超清母带",
    "sky": "沉浸环绕声",
    "jyeffect": "高清环绕声",
    "hires": "Hi-Res",
    "lossless": "无损",
    "exhigher": "极高(320k)",
    "higher": "较高(192k)",
    "standard": "标准(128k)",
}


class NeteaseAPIError(RuntimeError):
    pass


class NeteaseAPI:
    def __init__(self, cookies: dict | None = None):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Referer": "https://music.163.com"})
        if cookies:
            self.session.cookies.update(cookies)

    def _post(self, url: str, payload: dict) -> dict:
        resp = self.session.post(url, data=weapi(payload), timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_song_url(self, song_id: int, level: str) -> dict | None:
        data = self._post(
            "https://music.163.com/weapi/song/enhance/player/url/v1",
            {"ids": [song_id], "level": level, "encodeType": "aac"},
        )
        items = data.get("data") or []
        if not items or not items[0].get("url"):
            return None
        return items[0]

    def get_best_song_url(self, song_id: int, level: str | None) -> tuple[dict, str]:
        levels = [level] if level else QUALITY_CASCADE
        for lv in levels:
            item = self.get_song_url(song_id, lv)
            if item:
                return item, lv
        raise NeteaseAPIError(
            f"歌曲 {song_id} 无法获取播放地址（可能需要登录/大会员，或该歌曲已下架）"
        )

    def get_song_detail(self, song_ids: list[int]) -> dict[int, dict]:
        data = self._post(
            "https://music.163.com/weapi/v3/song/detail",
            {"c": json.dumps([{"id": i} for i in song_ids])},
        )
        result = {}
        for song in data.get("songs", []):
            album = song.get("al") or {}
            result[song["id"]] = {
                "name": song["name"],
                "artists": "/".join(a["name"] for a in song.get("ar", [])),
                "album": album.get("name", ""),
                "cover_url": album.get("picUrl", ""),
            }
        return result

    def get_playlist_tracks(self, playlist_id: int) -> dict:
        data = self._post(
            "https://music.163.com/weapi/v6/playlist/detail",
            {"id": playlist_id, "n": 100000, "s": 8},
        )
        playlist = data.get("playlist")
        if not playlist:
            raise NeteaseAPIError(f"歌单 {playlist_id} 不存在或不可访问")
        track_ids = [t["id"] for t in playlist.get("trackIds", [])]
        return {"name": playlist["name"], "track_ids": track_ids}
