import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from fileidentification.definitions.constants import ErrMsgFF
from fileidentification.definitions.models import SfInfo


def ffmpeg_inspect(sfinfo: SfInfo, verbose: bool) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Check for errors with ffprobe -show_error -> std.out shows the error, std.err has file information
    in verbose mode: run the file in ffmpeg dropping frames instead of showing it, returns stderr as string.
    depending on how many and how long the files are, this slows down the analytics
    When the file can't be opened by ffmpeg at all, it returns [True, "stderr"]. for minor errors [False, "stderr"].
    if everithing ok [False, ""]
    """

    cmd = f"ffprobe -hide_banner -show_error {shlex.quote(str(sfinfo.path))}"

    res = subprocess.run(cmd, check=False, shell=True, capture_output=True, text=True)
    if verbose:
        cmd_v = f"ffmpeg -v error -i {shlex.quote(str(sfinfo.path))} -f null -"
        res_v = subprocess.run(cmd_v, check=False, shell=True, capture_output=True, text=True)
        # replace the stdout of errors with the verbose one
        res.stdout = res_v.stderr
    return _parse_output(sfinfo, res.stdout, res.stderr, verbose)


def _parse_output(sfinfo: SfInfo, std_out: str, _: str, verbose: bool) -> tuple[bool, str, dict[str, Any] | None]:
    std_out = std_out.replace(f"{sfinfo.path.parent}", "")
    streams = ffmpeg_media_info(sfinfo.path)
    if verbose:
        if std_out:
            if any(msg in std_out for msg in ErrMsgFF):
                return True, std_out, streams
            return False, std_out, streams
        return False, std_out, streams

    if std_out:
        return True, std_out, streams
    return False, std_out, streams


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
