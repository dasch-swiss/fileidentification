import platform
import shlex
import subprocess
from pathlib import Path

from fileidentification.definitions.constants import PDFSETTINGS, Bin, LOPath
from fileidentification.definitions.models import PolicyParams, SfInfo

SOFFICE = LOPath.Linux if platform.system() == LOPath.Linux.name else LOPath.Darwin


def convert(sfinfo: SfInfo, args: PolicyParams) -> tuple[Path, str, Path]:
    """
    Convert a file to the desired format passed by the args

    :params sfinfo the metadata object of the file
    :params args the arguments how to convert {'bin', 'processing_args', 'target_container'}
    :params soffic the path to the libreOffice exec (default is Darwin

    :returns the constructed target path, the cmd run and the log path
    """

    wdir = Path(sfinfo.tdir / f"{sfinfo.filename.name}_{sfinfo.md5[:6]}")
    if not wdir.exists():
        wdir.mkdir(parents=True)

    target = Path(wdir / f"{sfinfo.filename.stem}.{args.target_container}")
    logfile_path = Path(wdir / f"{sfinfo.filename.stem}.log")

    # set input, outputfile and log for shell
    inputfile = shlex.quote(str(sfinfo.path))
    outfile = shlex.quote(str(target))
    logfile = shlex.quote(str(logfile_path))

    cmd: str = ""
    match args.bin:
        # construct command if its ffmpeg
        case Bin.FFMPEG:
            cmd = f"ffmpeg -y -i {inputfile} {args.processing_args} {outfile} 2> {logfile}"
        # construct command if its imagemagick
        case Bin.MAGICK:
            cmd = f"magick {args.processing_args} {inputfile} {outfile} 2> {logfile}"
        # construct command if its inkscape
        # case Bin.INCSCAPE:
        # cmd = f'inkscape --export-filename={outfile} {args["processing_args"]} {inputfile} 2> {logfile}'
        # construct command if its LibreOffice
        case Bin.SOFFICE:
            cmd = f"{SOFFICE} {args.processing_args} {args.target_container} {inputfile} "
            # add the version if its pdf
            if args.target_container == "pdf":
                cmd = f"{SOFFICE} {args.processing_args} 'pdf{PDFSETTINGS}' {inputfile} "
            cmd = cmd + f"--outdir {shlex.quote(str(wdir))} >> {logfile} 2>&1"

    # run cmd in shell (and as a string, so [error]output is redirected to logfile)
    subprocess.run(cmd, check=False, shell=True)

    return target, cmd, logfile_path
