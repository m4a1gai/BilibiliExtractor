from __future__ import annotations

import argparse
import re
from pathlib import Path

from ..common import config
from ..common.downloader import download_stream
from .api import QUALITY_NAMES, NeteaseAPI, NeteaseAPIError
from .login import qr_login

PLATFORM = "netease"
QUALITY_CHOICES = list(QUALITY_NAMES.keys())

TARGET_RE = re.compile(r"(?:https?://)?music\.163\.com/(?:#/)?(song|playlist)\?id=(\d+)")


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def extract_target(raw: str, forced_type: str | None) -> tuple[str, int]:
    raw = raw.strip()
    match = TARGET_RE.search(raw)
    if match:
        return forced_type or match.group(1), int(match.group(2))
    if raw.isdigit():
        return forced_type or "song", int(raw)
    raise SystemExit(f"无法从 '{raw}' 中识别出歌曲/歌单 ID，请提供纯数字 ID 或网易云音乐链接")


def extract_targets_from_text(text: str) -> list[tuple[str, int]]:
    """Finds every song/playlist reference in a text file: URLs first, then
    any line that's just a bare numeric id (treated as a song id)."""
    targets: list[tuple[str, int]] = []
    seen = set()
    for match in TARGET_RE.finditer(text):
        key = (match.group(1), int(match.group(2)))
        if key not in seen:
            seen.add(key)
            targets.append(key)
    for line in text.splitlines():
        line = line.strip()
        if line.isdigit():
            key = ("song", int(line))
            if key not in seen:
                seen.add(key)
                targets.append(key)
    return targets


def add_subparser(top_sub: argparse._SubParsersAction) -> None:
    parser = top_sub.add_parser("netease", help="网易云音乐歌曲/歌单提取")
    sub = parser.add_subparsers(dest="netease_command", required=True)

    login_p = sub.add_parser("login", help="扫码登录并保存 Cookie（可获取无损/Hi-Res 音质）")
    login_p.add_argument("--timeout", type=int, default=180, help="扫码超时时间（秒）")
    login_p.set_defaults(func=cmd_login)

    logout_p = sub.add_parser("logout", help="清除已保存的登录信息")
    logout_p.set_defaults(func=cmd_logout)

    dl_p = sub.add_parser("download", help="下载指定歌曲/歌单")
    dl_p.add_argument("target", help="歌曲/歌单 ID，或网易云音乐链接")
    dl_p.add_argument(
        "--type", choices=["auto", "song", "playlist"], default="auto",
        help="target 的类型，默认根据链接自动判断，纯数字 ID 默认按歌曲处理",
    )
    dl_p.add_argument("-o", "--output", default=".", help="输出目录，默认当前目录")
    dl_p.add_argument(
        "-q", "--quality", choices=QUALITY_CHOICES, default=None,
        help="指定音质，默认自动选账号能拿到的最高音质",
    )
    dl_p.set_defaults(func=cmd_download)

    batch_p = sub.add_parser("batch", help="从 txt 文件中提取所有歌曲/歌单并批量下载")
    batch_p.add_argument("file", help="txt 文件路径，逐行的纯数字 ID 或网易云音乐链接均可")
    batch_p.add_argument("-o", "--output", default=".", help="输出目录，默认当前目录")
    batch_p.add_argument(
        "-q", "--quality", choices=QUALITY_CHOICES, default=None,
        help="指定音质，默认自动选账号能拿到的最高音质",
    )
    batch_p.set_defaults(func=cmd_batch)


def cmd_login(args: argparse.Namespace) -> None:
    cookies = qr_login(timeout=args.timeout)
    config.save_cookies(PLATFORM, cookies)
    print(f"已保存登录信息到 {config.cookie_file(PLATFORM)}")


def cmd_logout(_args: argparse.Namespace) -> None:
    config.clear_cookies(PLATFORM)
    print("已清除登录信息")


def download_song(api: NeteaseAPI, song_id: int, args: argparse.Namespace, output_dir: Path) -> Path:
    detail = api.get_song_detail([song_id]).get(song_id, {"name": str(song_id), "artists": ""})
    item, level = api.get_best_song_url(song_id, args.quality)
    ext = item.get("type") or "mp3"
    title = f"{detail['artists']} - {detail['name']}" if detail["artists"] else detail["name"]
    safe_title = sanitize_filename(title)

    print(f"选择音质: {QUALITY_NAMES.get(level, level)}")
    dest = output_dir / f"{safe_title}.{ext}"
    download_stream(item["url"], dest, api.session, safe_title)
    return dest


def process_target(api: NeteaseAPI, target_type: str, target_id: int, args: argparse.Namespace, output_dir: Path) -> None:
    if target_type == "song":
        dest = download_song(api, target_id, args, output_dir)
        print(f"完成: {dest}")
        return

    playlist = api.get_playlist_tracks(target_id)
    track_ids = playlist["track_ids"]
    print(f"歌单《{playlist['name']}》共 {len(track_ids)} 首歌曲，将全部下载")
    playlist_dir = output_dir / sanitize_filename(playlist["name"])
    playlist_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for idx, song_id in enumerate(track_ids, start=1):
        print(f"\n[{idx}/{len(track_ids)}] 歌曲 ID {song_id}")
        try:
            dest = download_song(api, song_id, args, playlist_dir)
            print(f"完成: {dest}")
        except NeteaseAPIError as e:
            print(f"歌曲 {song_id} 下载失败: {e}")
            failed.append(song_id)

    if failed:
        raise SystemExit(f"\n共 {len(failed)} 首歌曲下载失败: {failed}")


def cmd_download(args: argparse.Namespace) -> None:
    cookies = config.load_cookies(PLATFORM)
    api = NeteaseAPI(cookies=cookies)
    if not cookies:
        print("提示：当前未登录，部分歌曲/音质可能无法获取。运行 'media-extractor netease login' 登录后可解锁无损/Hi-Res 音质及更多可播放歌曲。")

    forced_type = None if args.type == "auto" else args.type
    target_type, target_id = extract_target(args.target, forced_type)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        process_target(api, target_type, target_id, args, output_dir)
    except NeteaseAPIError as e:
        raise SystemExit(str(e))


def cmd_batch(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if not path.is_file():
        raise SystemExit(f"文件不存在: {path}")
    text = path.read_text(encoding="utf-8", errors="ignore")
    targets = extract_targets_from_text(text)
    if not targets:
        raise SystemExit(f"在 {path} 中没有找到任何歌曲/歌单 ID")
    print(f"共找到 {len(targets)} 个目标")

    cookies = config.load_cookies(PLATFORM)
    api = NeteaseAPI(cookies=cookies)
    if not cookies:
        print("提示：当前未登录，部分歌曲/音质可能无法获取。运行 'media-extractor netease login' 登录后可解锁无损/Hi-Res 音质及更多可播放歌曲。")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for idx, (target_type, target_id) in enumerate(targets, start=1):
        print(f"\n=== [{idx}/{len(targets)}] {target_type} {target_id} ===")
        try:
            process_target(api, target_type, target_id, args, output_dir)
        except (NeteaseAPIError, SystemExit) as e:
            print(f"{target_type} {target_id} 下载失败: {e}")
            failed.append((target_type, target_id))

    if failed:
        raise SystemExit(f"\n共 {len(failed)} 个目标下载失败: {failed}")
