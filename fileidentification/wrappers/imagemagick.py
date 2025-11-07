import shlex
import subprocess
from pathlib import Path

from fileidentification.definitions.settings import ErrMsgIM


def imagemagick_collect_warnings(file: Path, verbose: bool) -> tuple[bool, str, str]:
    """
    Check for errors with magick identify.
    Returns True if file is corrupt, stdout, technical metadata of the image
    """

    cmd = f'magick identify -format "%m %wx%h %g %z-bit %[channels]" {shlex.quote(str(file))}'

    if verbose:
        cmd = (
            f'magick identify -verbose -regard-warnings -format "%m %wx%h %g %z-bit %[channels]" '
            f"{shlex.quote(str(file))}"
        )
    res = subprocess.run(cmd, check=False, shell=True, capture_output=True, text=True)

    specs = res.stdout.replace(f"{file.parent}/", "")
    std_err = res.stderr.replace(f"{file.parent}/", "")

    if verbose:
        if std_err and any(msg in std_err for msg in ErrMsgIM):
            return True, std_err, specs
        return False, std_err, specs
    if std_err:
        return True, std_err, specs
    return False, std_err, specs


def imagemagick_media_info(file: Path) -> str:
    cmd = f'magick identify -format "%m %wx%h %g %z-bit %[channels]" {shlex.quote(str(file))}'
    res = subprocess.run(cmd, check=False, shell=True, capture_output=True, text=True)
    return res.stdout.replace(f"{file}/", "")
