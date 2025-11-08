import subprocess
from pathlib import Path


def imagemagick_collect_warnings(file: Path, verbose: bool) -> tuple[bool, str, str]:
    """
    Check for errors with magick identify.
    Returns True if file is corrupt, stdout, technical metadata of the image
    """

    cmd = ["identify", "-format", "%m %wx%h %g %z-bit %[channels]", str(file)]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    specs = res.stdout.replace(f"{file.parent}/", "")
    std_err = res.stderr.replace(f"{file.parent}/", "")

    if verbose:
        cmd_verbose = ["identify", "-verbose", "-regard-warnings", str(file)]
        res_verbose = subprocess.run(cmd_verbose, check=False, capture_output=True, text=True)
        std_err = res_verbose.stderr.replace(f"{file.parent}/", "")

    # rely on identify without -regard-warnings whether file is corrupt, but collect warnings
    if res.stderr:
        return True, std_err, specs
    return False, std_err, specs


def imagemagick_media_info(file: Path) -> str:
    cmd = ["identify", "-format", "%m %wx%h %g %z-bit %[channels]", str(file)]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return res.stdout.replace(f"{file}/", "")
