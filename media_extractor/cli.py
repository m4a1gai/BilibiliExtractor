from __future__ import annotations

import argparse
import sys

from .bilibili import cli as bilibili_cli
from .netease import cli as netease_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="media-extractor",
        description="多平台音视频提取工具（B 站 / 网易云音乐）",
    )
    sub = parser.add_subparsers(dest="platform", required=True)
    bilibili_cli.add_subparser(sub)
    netease_cli.add_subparser(sub)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(130)


if __name__ == "__main__":
    main()
