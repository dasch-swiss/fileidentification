import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from fileidentification.definitions.settings import ErrMsgFF


def ffmpeg_collect_warnings(file: Path, verbose: bool) -> tuple[bool, str, str]:
    """
    Check for errors with ffprobe -show_error or ffmpeg dropping frames.
    Returns True if file is corrupt, stdout, technical metadata of the video
    """

    cmd = f"ffprobe -hide_banner -show_error {shlex.quote(str(file))}"
    if verbose:
        cmd = f"ffmpeg -v error -i {shlex.quote(str(file))} -f null -"
    res = subprocess.run(cmd, check=False, shell=True, capture_output=True, text=True)
    if verbose:
        # ffmpeg catches errors in stderr, map the errors to stdout
        res.stdout = res.stderr

    std_out = res.stdout.replace(f"{file.parent}/", "")
    streams = ffmpeg_media_info(file)
    specs = json.dumps(streams) if streams else ""

    if verbose:
        if any(msg in std_out for msg in ErrMsgFF):
            return True, std_out, specs
        return False, std_out, specs
    if std_out:
        return True, std_out, specs
    return False, std_out, specs


def ffmpeg_media_info(file: Path) -> dict[str, Any] | None:
    cmd: list[str] = [
        "ffprobe",
        str(file),
        "-hide_banner",
        "-show_entries",
        "stream=index,codec_name,codec_long_name,profile,"
        "codec_tag,pix_fmt,color_space,coded_width,coded_height,r_frame_rate,bit_rate,channels,channel_layout,"
        "sample_aspect_ratio,display_aspect_ratio",
        "-output_format",
        "json",
    ]
    res = subprocess.run(cmd, check=False, capture_output=True)  # noqa: S603
    if res.returncode == 0:
        streams: dict[str, Any] = json.loads(res.stdout)["streams"]
        return streams
    return None
