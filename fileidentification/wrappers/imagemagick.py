import shlex
import subprocess
from pathlib import Path

from fileidentification.definitions.constants import ErrMsgIM
from fileidentification.definitions.models import SfInfo


def imagemagick_inspect(sfinfo: SfInfo, verbose: bool) -> tuple[bool, str, str]:
    """
    Run magick identify and if stderr, parse the stdout and grep some key sentences to decide
    whether it can be open at all. it returns [True, "stderr"]. for minor errors [False, "stderr"].
    if everithing ok [False, ""]
    """

    cmd = f'magick identify -format "%m %wx%h %g %z-bit %[channels]" {shlex.quote(str(sfinfo.path))}'

    if verbose:
        cmd = (
            f'magick identify -verbose -regard-warnings -format "%m %wx%h %g %z-bit %[channels]" '
            f"{shlex.quote(str(sfinfo.path))}"
        )
    res = subprocess.run(cmd, check=False, shell=True, capture_output=True, text=True)
    return _parse_output(sfinfo, res.stdout, res.stderr, verbose)


def _parse_output(sfinfo: SfInfo, std_out: str, std_err: str, verbose: bool) -> tuple[bool, str, str]:
    std_out = std_out.replace(f"{sfinfo.path.parent}", "")
    std_err = std_err.replace(f"{sfinfo.path.parent}", "")

    if verbose:
        if std_err and any(msg in std_err for msg in ErrMsgIM):
            return True, std_err, std_out
        return False, std_err, std_out

    if std_err:
        return True, std_err, std_out
    return False, std_err, std_out


def imagemagick_media_info(file: Path) -> str:
    cmd = f'magick identify -format "%m %wx%h %g %z-bit %[channels]" {shlex.quote(str(file))}'
    res = subprocess.run(cmd, check=False, shell=True, capture_output=True, text=True)
    return res.stdout.replace(f"{file}/", "")
