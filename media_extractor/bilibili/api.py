"""Thin client around the public Bilibili web API endpoints used to
resolve a BV id into playable video/audio stream URLs."""
from __future__ import annotations

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Bitmask requesting DASH streams with every extra feature (HDR, 4K,
# Dolby audio/vision, 8K, AV1) the account is entitled to.
FNVAL_DASH_ALL = 4048

QUALITY_NAMES = {
    127: "8K",
    126: "杜比视界",
    125: "HDR真彩",
    120: "4K",
    116: "1080P60",
    112: "1080P+",
    80: "1080P",
    74: "720P60",
    64: "720P",
    32: "480P",
    16: "360P",
}

AUDIO_QUALITY_NAMES = {
    30251: "Hi-Res无损",
    30250: "杜比全景声",
    30280: "192K",
    30232: "132K",
    30216: "64K",
}


class BilibiliAPIError(RuntimeError):
    pass


class BilibiliAPI:
    def __init__(self, cookies: dict | None = None):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})
        if cookies:
            self.session.cookies.update(cookies)
        self._ensure_buvid()

    def _ensure_buvid(self) -> None:
        """Bilibili's risk control rejects requests with no buvid3 cookie."""
        if self.session.cookies.get("buvid3"):
            return
        try:
            resp = self.session.get(
                "https://api.bilibili.com/x/frontend/finger/spi", timeout=10
            )
            data = resp.json().get("data", {})
            if data.get("b_3"):
                self.session.cookies.set("buvid3", data["b_3"], domain=".bilibili.com")
        except requests.RequestException:
            pass

    def _get_json(self, url: str, params: dict, referer: str) -> dict:
        resp = self.session.get(
            url, params=params, headers={"Referer": referer}, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise BilibiliAPIError(f"{url} -> code={data.get('code')} msg={data.get('message')}")
        return data["data"]

    def get_video_info(self, bvid: str) -> dict:
        """Returns title, aid and the list of parts (cid per page)."""
        referer = f"https://www.bilibili.com/video/{bvid}"
        data = self._get_json(
            "https://api.bilibili.com/x/web-interface/view",
            {"bvid": bvid},
            referer,
        )
        return {
            "bvid": data["bvid"],
            "aid": data["aid"],
            "title": data["title"],
            "cover_url": data.get("pic", ""),
            "pages": [
                {"cid": p["cid"], "page": p["page"], "part": p["part"]}
                for p in data["pages"]
            ],
        }

    def get_play_streams(self, bvid: str, cid: int, qn: int = 127) -> dict:
        """Returns the best available DASH video/audio stream URLs.

        The response already reflects what the account (anonymous or
        logged-in, VIP or not) is allowed to fetch -- no cookie means
        Bilibili silently caps quality around 480p/720p.
        """
        referer = f"https://www.bilibili.com/video/{bvid}"
        data = self._get_json(
            "https://api.bilibili.com/x/player/playurl",
            {
                "bvid": bvid,
                "cid": cid,
                "qn": qn,
                "fnval": FNVAL_DASH_ALL,
                "fourk": 1,
            },
            referer,
        )
        dash = data.get("dash")
        if not dash:
            raise BilibiliAPIError(
                "该视频未返回 DASH 流（可能是番剧/互动视频等特殊类型，暂不支持）"
            )
        videos = sorted(dash["video"], key=lambda v: v["id"], reverse=True)
        audios = sorted(dash.get("audio") or [], key=lambda a: a["id"], reverse=True)
        # Hi-Res lossless (FLAC) and Dolby Atmos are only present here, not
        # mixed into dash["audio"], and only when the account is entitled.
        flac = dash.get("flac") or {}
        hires_audio = flac.get("audio")
        dolby_audios = (dash.get("dolby") or {}).get("audio") or []
        return {
            "accept_quality": data.get("accept_description", []),
            "videos": videos,
            "audios": audios,
            "hires_audio": hires_audio,
            "dolby_audio": dolby_audios[0] if dolby_audios else None,
            "referer": referer,
        }
