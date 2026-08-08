"""Muxing helpers around the ffmpeg CLI."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def remux(src: Path, dest: Path) -> None:
    """Copies a single raw DASH stream into a standard container (no re-encode)."""
    _run(["ffmpeg", "-y", "-i", str(src), "-c", "copy", str(dest)])


def merge(video: Path, audio: Path, dest: Path) -> None:
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(audio),
            "-c", "copy",
            str(dest),
        ]
    )


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 执行失败: {result.stderr.decode(errors='ignore')}")
