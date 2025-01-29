import subprocess
import json
import shlex
import os
from abc import ABC
from pathlib import Path
from typing import Union, Any
from conf.models import SFoutput, SfInfo
from conf.settings import SiegfriedConf, LibreOfficePath, ErrorMsgFF, ErrorMsgIM, LibreOfficePdfSettings, Bin


class Analytics(ABC):

    @staticmethod
    def is_corrupt(sfinfo: SfInfo, verbose: bool = False) -> tuple[bool, str, str | dict[str, Any] | None]:
        ...

    @staticmethod
    def parse_output(sfinfo: SfInfo, std_out, std_err, verbose: bool = False) \
            -> tuple[bool, str, str | dict[str, Any] | None]:
        ...

class Siegfried:
    @staticmethod
    def analyse(path: Union[str, Path]) -> list[SFoutput]:
        """analyse a file or folder recursively, returns a list of files with the information
        gathered with siegfried in json"""
        res = subprocess.run(["sf", "-json", "-hash", SiegfriedConf.ALG,
                              "-multi", SiegfriedConf.MULTI,  path], capture_output=True, text=True)
        res.check_returncode()
        res = json.loads(res.stdout)
        return res['files']


class Ffmpeg(Analytics):

    @staticmethod
    def is_corrupt(sfinfo: SfInfo, verbose: bool = False ) -> tuple[bool, str, dict[str, Any] | None]:
        """
        check for errors with ffprobe -show_error -> std.out shows the error, std.err has file information
        in verbose mode: run the file in ffmpeg dropping frames instead of showing it, returns stderr as string.
        depending on how many and how long the files are, this slows down the analytics
        When the file can't be opened by ffmpeg at all, it returns [True, "stderr"]. for minor errors [False, "stderr"].
        if everithing ok [False, ""]"""

        cmd = f'ffprobe -hide_banner -show_error {shlex.quote(str(sfinfo.path))}'

        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if verbose:
            cmd_v = f'ffmpeg -v error -i {shlex.quote(str(sfinfo.path))} -f null -'
            res_v = subprocess.run(cmd_v, shell=True, capture_output=True, text=True)
            # replace the stdout of errors with the verbose one
            res.stdout = res_v.stderr
        return Ffmpeg.parse_output(sfinfo, res.stdout, res.stderr, verbose)


    @staticmethod
    def parse_output(sfinfo: SfInfo, std_out, _, verbose: bool = False) -> tuple[bool, str, dict[str, Any] | None]:

        std_out = std_out.replace(f'{sfinfo.path}/', "")
        streams = Ffmpeg.codec_info(sfinfo.path)
        if verbose:
            if std_out:
                if any([msg in std_out for msg in ErrorMsgFF]):
                    return True, std_out, streams
                return False, std_out, streams
            return False, std_out, streams

        if std_out:
            return True, std_out, streams
        return False, std_out, streams

    @staticmethod
    def codec_info(file: Path) -> dict[str, Any] | None:
        cmd = ["ffprobe", file, "-hide_banner", "-show_entries", "stream=index,codec_name,codec_long_name,profile,"
               "codec_tag,pix_fmt,color_space,coded_width,coded_height,r_frame_rate,bit_rate,channels,channel_layout,"
               "sample_aspect_ratio,display_aspect_ratio", "-output_format", "json"]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode == 0:
            streams = json.loads(res.stdout)['streams']
            return streams
        return


class ImageMagick(Analytics):

    @staticmethod
    def is_corrupt(sfinfo: SfInfo, verbose: bool = False) -> tuple[bool, str, str]:
        """run magick identify and if stderr, parse the stdout and grep some key sentences to decide
        whether it can be open at all. it returns [True, "stderr"]. for minor errors [False, "stderr"].
        if everithing ok [False, ""]"""

        cmd = f'magick identify -regard-warnings -format "%m %wx%h %g %z-bit %[channels]" {shlex.quote(str(sfinfo.path))}'

        if verbose:
            cmd = (f'magick identify -verbose -regard-warnings -format "%m %wx%h %g %z-bit %[channels]" '
                   f'{shlex.quote(str(sfinfo.path))}')
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return ImageMagick.parse_output(sfinfo, res.stdout, res.stderr)

    @staticmethod
    def parse_output(sfinfo: SfInfo, std_out, std_err, verbose: bool = False) -> tuple[bool, str, str]:

        std_out = std_out.replace(f'{sfinfo.path}/', "")
        std_err = std_err.replace(f'{sfinfo.path}/', "")

        if std_err:
            if any([msg in std_err for msg in ErrorMsgIM]):
                return True, std_err, std_out
            return False, std_err, std_out
        return False, std_err, std_out

    @staticmethod
    def codec_info(file: Path) -> Union[str | None]:

        cmd = f'magick identify -format "%m %wx%h %g %z-bit %[channels]" {shlex.quote(str(file))}'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return res.stdout.replace(f'{file}/', "")


class Converter:
    @staticmethod
    def convert(sfinfo: SfInfo, args: dict, soffice: Path = LibreOfficePath.Darwin) -> tuple[Path, str, Path]:
        """converts a file (filepath from SfInfo.filename to the desired format passed by the args

        :params sfinfo the metadata object of the file
        :params args the arguments how to convert {'bin', 'processing_args', 'target_container'}
        :params soffic the path to the libreOffice exec (default is Darwin

        :returns the constructed target path, the cmd run and the log path
        """

        wdir = Path(sfinfo.wdir / f'{sfinfo.filename.stem}_{sfinfo.filehash[:6]}')
        if not wdir.exists():
            os.makedirs(wdir)

        # TODO Metadata such as exif... are lost when reencoded,
        #  need to implement something to copy some parts of these metadata?

        target = Path(wdir / f'{sfinfo.filename.stem}.{args["target_container"]}')
        logfile_path = Path(wdir / f'{sfinfo.filename.stem}.log')

        # set input, outputfile and log for shell
        inputfile = shlex.quote(str(sfinfo.path))
        outfile = shlex.quote(str(target))
        logfile = shlex.quote(str(logfile_path))

        match args["bin"]:
            # construct command if its ffmpeg
            case Bin.FFMPEG:
                cmd = f'ffmpeg -y -i {inputfile} {args["processing_args"]} {outfile} 2> {logfile}'
            # construct command if its imagemagick
            case Bin.MAGICK:
                cmd = f'magick {args["processing_args"]} {inputfile} {outfile} 2> {logfile}'
            # construct command if its inkscape
            case Bin.INCSCAPE:
                cmd = f'inkscape --export-filename={outfile} {args["processing_args"]} {inputfile} 2> {logfile}'
            # construct command if its LibreOffice
            case Bin.SOFFICE:
                cmd = f'{soffice} {args["processing_args"]} {args["target_container"]} {inputfile} '
                # add the version if its pdf
                if args["target_container"] == "pdf":
                    cmd = f'{soffice} {args["processing_args"]} \'pdf{LibreOfficePdfSettings.version2a}\' {inputfile} '
                cmd = cmd + f'--outdir {shlex.quote(str(wdir))} > {logfile}'
            case _:
                print(f'unknown bin {args["bin"]} in policies. aborting ...')
                quit()

        # run cmd in shell (and as a string, so [error]output is redirected to logfile)
        subprocess.run(cmd, shell=True)

        return target, cmd, logfile_path


class Rsync:

    @staticmethod
    def copy(source: str | Path, dest: str | Path) -> tuple[bool, str, list]:
        """rsync the source to dest.
        :returns True, stderr, cmd if there was an error, else False, stderr, cmd"""
        cmd = ['rsync', '-avh', str(source), str(dest)]
        res = subprocess.run(cmd, capture_output=True)  # output in stderr and b'', because of certain char issues
        if res.returncode != 0:
            return True, res.stderr.decode("utf-8", "backslashreplace"), cmd
        return False, res.stderr.decode("utf-8", "backslashreplace"), cmd
