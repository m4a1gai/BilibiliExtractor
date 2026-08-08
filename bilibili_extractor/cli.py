from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

from . import config
from .api import AUDIO_QUALITY_NAMES, BilibiliAPI, BilibiliAPIError, QUALITY_NAMES
from .downloader import download_stream
from .login import qr_login
from .merger import ffmpeg_available, merge, remux

BVID_RE = re.compile(r"(BV[0-9A-Za-z]{10})")


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def extract_bvid(raw: str) -> str:
    match = BVID_RE.search(raw)
    if not match:
        raise SystemExit(f"无法从 '{raw}' 中识别出 BV 号")
    return match.group(1)


def pick_video(videos: list[dict], quality: int | None) -> dict:
    if quality is not None:
        for v in videos:
            if v["id"] == quality:
                return v
        available = sorted({v["id"] for v in videos}, reverse=True)
        raise SystemExit(
            f"该视频没有 qn={quality} 的画质，可用画质: "
            f"{[QUALITY_NAMES.get(q, q) for q in available]}"
        )
    return videos[0]


def pick_audio(streams: dict) -> tuple[dict | None, str, str]:
    """Prefers Hi-Res lossless (FLAC) over the best regular AAC track.

    Hi-Res is a separate field in the API response and only ever present
    if the logged-in account is entitled to it (大会员 + Hi-Res 无损包).
    """
    hires = streams.get("hires_audio")
    if hires:
        return hires, "flac", AUDIO_QUALITY_NAMES.get(hires["id"], str(hires["id"]))
    if streams["audios"]:
        audio = streams["audios"][0]
        return audio, "m4a", AUDIO_QUALITY_NAMES.get(audio["id"], str(audio["id"]))
    return None, "m4a", ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bilibili-extractor",
        description="根据 BV 号提取 B 站视频/音频文件",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    login_p = sub.add_parser("login", help="扫码登录并保存 Cookie（可获取更高画质）")
    login_p.add_argument("--timeout", type=int, default=180, help="扫码超时时间（秒）")

    logout_p = sub.add_parser("logout", help="清除已保存的登录信息")

    dl_p = sub.add_parser("download", help="下载指定 BV 号的视频/音频")
    dl_p.add_argument("bvid", help="BV 号，或包含 BV 号的完整视频链接")
    dl_p.add_argument("-o", "--output", default=".", help="输出目录，默认当前目录")
    page_group = dl_p.add_mutually_exclusive_group()
    page_group.add_argument("-p", "--page", type=int, default=1, help="分P序号（从1开始），默认第1P")
    page_group.add_argument("-a", "--all-pages", action="store_true", help="下载该视频的所有分P")
    dl_p.add_argument(
        "-q", "--quality", type=int, default=None,
        help="指定画质 qn 值（如 80=1080P，64=720P），默认自动选最高可用画质",
    )
    mode = dl_p.add_mutually_exclusive_group()
    mode.add_argument("--audio-only", action="store_true", help="只提取音频（输出 m4a）")
    mode.add_argument("--video-only", action="store_true", help="只提取无声视频（输出 mp4）")

    batch_p = sub.add_parser("batch", help="从 txt 文件中提取所有 BV 号并批量下载")
    batch_p.add_argument("file", help="txt 文件路径，会自动提取文本中出现的所有 BV 号")
    batch_p.add_argument("-o", "--output", default=".", help="输出目录，默认当前目录")
    batch_page_group = batch_p.add_mutually_exclusive_group()
    batch_page_group.add_argument("-p", "--page", type=int, default=1, help="每个视频下载第几P（从1开始），默认第1P")
    batch_page_group.add_argument("-a", "--all-pages", action="store_true", help="每个视频下载所有分P")
    batch_p.add_argument(
        "-q", "--quality", type=int, default=None,
        help="指定画质 qn 值（如 80=1080P，64=720P），默认自动选最高可用画质",
    )
    batch_mode = batch_p.add_mutually_exclusive_group()
    batch_mode.add_argument("--audio-only", action="store_true", help="只提取音频（输出 m4a）")
    batch_mode.add_argument("--video-only", action="store_true", help="只提取无声视频（输出 mp4）")

    return parser


def cmd_login(args: argparse.Namespace) -> None:
    cookies = qr_login(timeout=args.timeout)
    config.save_cookies(cookies)
    print(f"已保存登录信息到 {config.COOKIE_FILE}")


def cmd_logout(_args: argparse.Namespace) -> None:
    config.clear_cookies()
    print("已清除登录信息")


def download_page(api: BilibiliAPI, bvid: str, info: dict, page_num: int, args: argparse.Namespace, output_dir: Path) -> Path:
    """Downloads a single page (分P) of a video, returns the output file path."""
    pages = info["pages"]
    part = pages[page_num - 1]
    title = info["title"] if len(pages) == 1 else f"{info['title']}_P{page_num}_{part['part']}"
    safe_title = sanitize_filename(title)

    print(f"正在解析播放地址: {safe_title}")
    streams = api.get_play_streams(bvid, part["cid"])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        referer = streams["referer"]

        video_path = None
        audio_path = None

        if not args.audio_only:
            video = pick_video(streams["videos"], args.quality)
            print(f"选择画质: {QUALITY_NAMES.get(video['id'], video['id'])}")
            video_path = tmp_dir / "video.m4s"
            download_stream(video["baseUrl"], referer, video_path, api.session, "视频")

        audio_ext = "m4a"
        if not args.video_only:
            audio, audio_ext, audio_label = pick_audio(streams)
            if audio is None:
                if args.audio_only:
                    raise SystemExit("该视频没有可用的音频流")
            else:
                print(f"选择音质: {audio_label}")
                audio_path = tmp_dir / "audio.m4s"
                download_stream(audio["baseUrl"], referer, audio_path, api.session, "音频")

        if video_path and audio_path:
            # MP4 can't carry a FLAC track; fall back to Matroska which copies any codec untouched.
            container = "mkv" if audio_ext == "flac" else "mp4"
            dest = output_dir / f"{safe_title}.{container}"
            print("正在合并音视频...")
            merge(video_path, audio_path, dest)
        elif video_path:
            dest = output_dir / f"{safe_title}.mp4"
            remux(video_path, dest)
        elif audio_path:
            dest = output_dir / f"{safe_title}.{audio_ext}"
            remux(audio_path, dest)
        else:
            raise SystemExit("没有需要下载的内容")

    return dest


def process_video(api: BilibiliAPI, bvid: str, args: argparse.Namespace, output_dir: Path) -> None:
    """Downloads one BV video according to args.page / args.all_pages."""
    print(f"正在获取视频信息: {bvid}")
    info = api.get_video_info(bvid)
    pages = info["pages"]

    if args.all_pages:
        print(f"该视频共 {len(pages)} P，将全部下载")
        failed = []
        for page_num in range(1, len(pages) + 1):
            print(f"\n[{page_num}/{len(pages)}] {pages[page_num - 1]['part']}")
            try:
                dest = download_page(api, bvid, info, page_num, args, output_dir)
                print(f"完成: {dest}")
            except (BilibiliAPIError, SystemExit) as e:
                print(f"第 {page_num} P 下载失败: {e}")
                failed.append(page_num)
        if failed:
            raise SystemExit(f"共 {len(failed)} P 下载失败: {failed}")
        return

    if args.page < 1 or args.page > len(pages):
        raise SystemExit(f"该视频共 {len(pages)} P，-p 需在 1~{len(pages)} 之间")

    dest = download_page(api, bvid, info, args.page, args, output_dir)
    print(f"完成: {dest}")


def cmd_download(args: argparse.Namespace) -> None:
    if not ffmpeg_available():
        raise SystemExit("未检测到 ffmpeg，请先安装 ffmpeg 并加入 PATH")

    bvid = extract_bvid(args.bvid)
    cookies = config.load_cookies()
    api = BilibiliAPI(cookies=cookies)
    if not cookies:
        print("提示：当前未登录，画质可能被限制在 480P 左右。运行 'bilibili-extractor login' 可解锁更高画质。")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        process_video(api, bvid, args, output_dir)
    except BilibiliAPIError as e:
        raise SystemExit(str(e))


def cmd_batch(args: argparse.Namespace) -> None:
    if not ffmpeg_available():
        raise SystemExit("未检测到 ffmpeg，请先安装 ffmpeg 并加入 PATH")

    path = Path(args.file)
    if not path.is_file():
        raise SystemExit(f"文件不存在: {path}")
    text = path.read_text(encoding="utf-8", errors="ignore")
    bvids = list(dict.fromkeys(BVID_RE.findall(text)))  # dedupe, keep order
    if not bvids:
        raise SystemExit(f"在 {path} 中没有找到任何 BV 号")
    print(f"共找到 {len(bvids)} 个 BV 号")

    cookies = config.load_cookies()
    api = BilibiliAPI(cookies=cookies)
    if not cookies:
        print("提示：当前未登录，画质可能被限制在 480P 左右。运行 'bilibili-extractor login' 可解锁更高画质。")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for idx, bvid in enumerate(bvids, start=1):
        print(f"\n=== [{idx}/{len(bvids)}] {bvid} ===")
        try:
            process_video(api, bvid, args, output_dir)
        except (BilibiliAPIError, SystemExit) as e:
            print(f"{bvid} 下载失败: {e}")
            failed.append(bvid)

    if failed:
        raise SystemExit(f"\n共 {len(failed)} 个视频下载失败: {failed}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "login":
            cmd_login(args)
        elif args.command == "logout":
            cmd_logout(args)
        elif args.command == "download":
            cmd_download(args)
        elif args.command == "batch":
            cmd_batch(args)
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(130)


if __name__ == "__main__":
    main()
