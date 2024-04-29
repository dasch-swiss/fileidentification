import subprocess
import json
import shlex
import os
from abc import ABC
from pathlib import Path
from typing import Union
from conf.models import SiegfriedConf, SFoutput, SfInfo, LibreOfficePath, ErrorMsgFF, ErrorMsgIM, ServerCon, LibreOfficePdfSettings


class Analytics(ABC):

    @staticmethod
    def is_corrupt(sfinfo: SfInfo, dry: bool = False, verbose: bool = False) -> tuple[bool, str, str]:
        ...

    @staticmethod
    def parse_output(sfinfo: SfInfo, std_out, std_err, verbose: bool = False) -> tuple[bool, str, str]:
        ...

class Siegfried:
    @staticmethod
    def analyse(path: Union[str, Path], to_file: Path = None) -> list[SFoutput]:
        """analyse a file or folder recursively, returns a list of files with the information
        gathered with siegfried in json"""
        res = subprocess.run(["sf", "-json", "-hash", SiegfriedConf.ALG,
                              "-multi", SiegfriedConf.MULTI,  path], capture_output=True, text=True)
        res.check_returncode()
        res = json.loads(res.stdout)
        return res['files']


class Ffmpeg(Analytics):

    @staticmethod
    def is_corrupt(sfinfo: SfInfo, dry: bool = False, verbose: bool = False ) -> tuple[bool, str, str]:
        """
        check for errors with ffprobe -show_error -> std.out shows the error, std.err has file information
        in verbose mode: run the file in ffmpeg dropping frames instead of showing it, returns stderr as string.
        depending on how many and how long the files are, this slows down the analytics
        When the file can't be opened by ffmpeg at all, it returns [True, "stderr"]. for minor errors [False, "stderr"].
        if everithing ok [False, ""]"""

        cmd = f'ffprobe -hide_banner -show_error {shlex.quote(str(sfinfo.filename))}'
        if dry:
            return False, cmd, ""
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if verbose:
            cmd_v = f'ffmpeg -v error -i {shlex.quote(str(sfinfo.filename))} -f null -'
            res_v = subprocess.run(cmd_v, shell=True, capture_output=True, text=True)
            # replace the stdout of errors with the verbose one
            res.stdout = res_v.stderr
        return Ffmpeg.parse_output(sfinfo, res.stdout, res.stderr, verbose)


    @staticmethod
    def parse_output(sfinfo: SfInfo, std_out, std_err, verbose: bool = False) -> tuple[bool, str, str]:
        ####
        # this is bit hackish, but does the job for now
        # to get the file information, we use the header metadata from std.err for the files that passed
        # (its already nice formatted) -> so std_err and std_out gets inverted

        # ffprobe has also a flag -output_format json
        # the information could be parsed better and in a more structured way, if needed
        # for now, we're just strippin the relative paths out of the string return of ffprobe
        # and look for keyword if verbose

        std_out = std_out.replace(f'{sfinfo.files_dir}/', "").replace(f'{sfinfo.wdir}/', "")
        std_err = std_err.replace(f'{sfinfo.files_dir}/', "").replace(f'{sfinfo.wdir}/', "")
        if verbose:
            if std_out:
                if any([msg in std_out for msg in ErrorMsgFF]):
                    return True, std_out, std_err
                return False, std_out, std_err
            return False, std_out, std_err

        if std_out:
            return True, std_out, std_err
        return False, std_out, std_err


class ImageMagick(Analytics):

    @staticmethod
    def is_corrupt(sfinfo: SfInfo, dry: bool = False, verbose: bool = False) -> tuple[bool, str, str]:
        """run imagemagick identify and if stderr, parse the stdout and grep some key sentences to decide
        whether it can be open at all. it returns [True, "stderr"]. for minor errors [False, "stderr"].
        if everithing ok [False, ""]"""

        cmd = f'magick identify -regard-warnings {shlex.quote(str(sfinfo.filename))}'
        if dry:
            return False, cmd, ""
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return ImageMagick.parse_output(sfinfo, res.stdout, res.stderr)

    @staticmethod
    def parse_output(sfinfo: SfInfo, std_out, std_err, verbose: bool = False) -> tuple[bool, str, str]:

        std_out = std_out.replace(f'{sfinfo.files_dir}/', "").replace(f'{sfinfo.wdir}/', "")
        std_err = std_err.replace(f'{sfinfo.files_dir}/', "").replace(f'{sfinfo.wdir}/', "")

        if std_err:
            if any([msg in std_err for msg in ErrorMsgIM]):
                return True, std_err, std_out
            return False, std_err, std_out
        return False, std_err, std_out


class Converter:
    @staticmethod
    def convert(sfinfo: SfInfo, args: dict, soffice: Path = LibreOfficePath.Darwin, dry: bool = False)\
            -> tuple[Path, str, Path]:
        """converts a file (filepath from SfInfo.filename to the desired format passed by the args

        :params sfinfo the metadata object of the file
        :params args the arguments how to convert {'bin', 'processing_args', 'target_container'}
        :params soffic the path to the libreOffice exec (default is Darwin

        :returns the constructed target path, the cmd run and the log path
        """

        wdir = Path(sfinfo.wdir / sfinfo.relative_path / Path(f'{sfinfo.filename.stem}_{sfinfo.filehash}'))
        if not wdir.exists() and not dry:
            os.makedirs(wdir)

        # TODO Metadata such as exif... are lost when reencoded,
        #  need to implement something to copy some parts of these metadata?

        target = Path(wdir / f'{sfinfo.filename.stem}.{args["target_container"]}')
        logfile_path = Path(wdir / f'{sfinfo.filename.stem}.log')

        # set input, outputfile and log for shell
        inputfile = shlex.quote(str(sfinfo.filename))
        outfile = shlex.quote(str(target))
        logfile = shlex.quote(str(logfile_path))

        match args["bin"]:
            # construct command if its ffmpeg
            case "ffmpeg":
                cmd = f'ffmpeg -y -i {inputfile} {args["processing_args"]} {outfile} 2> {logfile}'
            # construct command if its imagemagick
            case "convert":
                cmd = f'convert {args["processing_args"]} {inputfile} {outfile} 2> {logfile}'
            # construct command if its LibreOffice
            case "soffice":
                cmd = f'{soffice} {args["processing_args"]} {args["target_container"]} {inputfile} '
                # add the version if its pdf
                if args["target_container"] == "pdf":
                    cmd = f'{soffice} {args["processing_args"]} \'pdf{LibreOfficePdfSettings.version2a}\' {inputfile} '
                cmd = cmd + f'--outdir {shlex.quote(str(wdir))} > {logfile}'
            case _:
                print(f'unknown bin {args["bin"]} in policies. aborting ...')
                quit()

        if not dry:
            # run cmd in shell (and as a string, so [error]output is redirected to logfile)
            subprocess.run(cmd, shell=True)

        return target, cmd, logfile_path


class Rsync:

    @staticmethod
    def copy(source: str, dest: str, dry: bool = False,
             server: ServerCon = None) -> tuple[bool, str, list]:
        """rsync the source to dest. if rsync did not return an error, delete source
        :returns True, stderr, cmd if there was an error, else False, stdout, cmd"""
        cmd = ['rsync', '-av', source, dest]
        if server:
            cmd = ['rsync', '-av', source, f'{server.user}@{server.ip}:{dest}']
        if not dry:
            res = subprocess.run(cmd, capture_output=True)
            if res.stderr:
                return True, res.stderr.decode("utf-8", "backslashreplace"), cmd
            # if there is no error and not remote, remove original
            if not server:
                os.remove(source)
            return False, res.stdout.decode("utf-8", "backslashreplace"), cmd
        else:
            return False, "", cmd

    @staticmethod
    def fetch(source: str, dest: str, server: ServerCon, dry: bool = False) -> tuple[bool, str, list]:
        if f'{server.user}/' in source:
            source = source.split(f'{server.user}/')[1]
        cmd = ['rsync', '-av', f'{server.user}@{server.ip}:{source}', dest+"/"]
        if not dry:
            res = subprocess.run(cmd, capture_output=True)
            if res.stderr:
                return True, res.stderr.decode("utf-8", "backslashreplace"), cmd
            return False, res.stdout.decode("utf-8", "backslashreplace"), cmd
        else:
            return False, "", cmd


