from __future__ import annotations
import os
import platform
import shutil
import json
import csv
import typer
import pygfried
from time import time
from datetime import datetime
from typer import secho, colors
from typing import Any
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
from dataclasses import dataclass
from fileidentification.wrappers.wrappers import Ffmpeg, Converter as Con, ImageMagick, Rsync
from fileidentification.output import print_fileformats, print_diagnostic, print_siegfried_errors, print_duplicates, print_processing_errors
from fileidentification.conf.settings import (PathsConfig, LibreOfficePath, FileDiagnosticsMsg, PolicyMsg, FileProcessingMsg,
                                              JsonOutput, Bin, ErrMsgReencode, CSVFIELDS)
from fileidentification.models import SfInfo, BasicAnalytics, LogTables, LogMsg, LogOutput
from fileidentification.policies.policies import generate_policies, PolicyParams
from fileidentification.policies.default import systemfiles
from fileidentification.helpers import sfinfo2csv

@dataclass
class Mode:
    """the different modes for the FileHanlder.
    REMOVEORIGINAL: bool, whether to remove the original files of the files that got converted
    VERBOSE: bool, do verbose analysis of video and image files
    STRICT: bool, move files that are not listed in policies to FAILED instead of skipping them
    QUIET: bool, just print warnings and errors"""
    REMOVEORIGINAL: bool = False
    VERBOSE: bool = False
    STRICT: bool = False
    QUIET: bool = False


class FileHandler:
    """
    It can create, verify and apply policies, test the integrity of the files and convert them (with FileConverter) and
    move and remove tmp files.
    """

    def __init__(self) -> None:

        self.mode: Mode = Mode()
        self.fmt2ext: dict[str, Any] = json.loads(Path(PathsConfig.FMT2EXT).read_text())
        self.policies: dict[str, Any] = {}
        self.log_tables = LogTables()
        self.ba = BasicAnalytics()
        self.stack: list[SfInfo] = []
        self.wdir: Path = Path(PathsConfig.WDIR)
        self.converter = FileConverter()

    def _integrity_test(self, sfinfo: SfInfo) -> None:

        puid = sfinfo.processed_as
        if not puid:
            self._remove(sfinfo)
            sfinfo.processing_logs.append(LogMsg(name="filehandler", msg="file removed"))
            msg = LogMsg(name='filehandler', msg=f'{FileProcessingMsg.PUIDFAIL} for {sfinfo.filename}')
            self.log_tables.errors.append((msg, sfinfo))
            return

        if sfinfo.errors == FileDiagnosticsMsg.EMPTYSOURCE:
            self._remove(sfinfo)
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileDiagnosticsMsg.ERROR}'))
            self.log_tables.diagnostics_add(sfinfo, FileDiagnosticsMsg.EMPTYSOURCE)
            return

        # os specific files we do not care, eg .DS_store etc
        if puid in systemfiles:  # ['fmt/394']:
            # could also simply remove them
            # os.remove(sfinfo.path)
            return

        # case where there is an extension missmatch, rename the file if there is a unique ext
        if sfinfo.matches[0]["warning"] == FileDiagnosticsMsg.EXTMISMATCH:
            if len(self.fmt2ext[puid]['file_extensions']) == 1:
                ext = "." + self.fmt2ext[puid]['file_extensions'][-1]
                self._rename(sfinfo, ext)
            else:
                msg = f'expecting one of the following ext: {[el for el in self.fmt2ext[puid]["file_extensions"]]}'  # type: ignore
                sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=msg))  # type: ignore
                secho(f'\nWARNING: you should manually rename {sfinfo.filename}\n{msg}', fg=colors.YELLOW)
            self.log_tables.diagnostics_add(sfinfo, FileDiagnosticsMsg.EXTMISMATCH)

        # check if the file throws any errors while open/processing it with the respective bin
        if self._is_file_corrupt(sfinfo):
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileDiagnosticsMsg.ERROR}'))
            self._remove(sfinfo)
            return

    def _apply_policy(self, sfinfo: SfInfo) -> None:

        puid = sfinfo.processed_as
        if not puid:
            return
        if sfinfo.status.pending:
            return

        if puid not in self.policies:
            # in strict mode, move file
            if self.mode.STRICT:
                sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{PolicyMsg.NOTINPOLICIES}'))
                self._remove(sfinfo)
                return
            # just flag it as skipped
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{PolicyMsg.SKIPPED}'))
            return

        # case where file needs to be converted
        if not self.policies[puid]['accepted']:
            sfinfo.status.pending = True
            return

        # check if mp4 has correct stream (i.e. h264 and aac)
        if puid in ['fmt/199']:
            if not self._has_valid_streams(sfinfo):
                sfinfo.status.pending = True
                return

    def _remove(self, sfinfo: SfInfo) -> None:
        dest = Path(sfinfo.wdir / f'{PathsConfig.REMOVED}' / sfinfo.filename.parent)
        if not dest.exists():
            os.makedirs(dest)
        err, msg, cmd = Rsync.copy(sfinfo.path, dest)
        # if there was an error, append to processing err tables
        if err:
            secho(f'{FileProcessingMsg.FAILEDMOVE} {cmd}', fg=colors.RED)
            self.log_tables.errors.append((LogMsg(name='rsync', msg=msg), sfinfo))
        else:
            os.remove(sfinfo.path)
        sfinfo.status.removed = True
        if sfinfo.processed_as:
            self.ba.puid_unique[sfinfo.processed_as].remove(sfinfo)

    def _rename(self, sfinfo: SfInfo, ext: str) -> None:
        dest = sfinfo.path.with_suffix(ext)
        # if a file with same name and extension already there, append file hash to name
        if sfinfo.path.with_suffix(ext).is_file():
            dest = sfinfo.path.parent / f'{sfinfo.path.stem}_{sfinfo.md5[:6]}{ext}'
        os.rename(sfinfo.path, dest)
        msg = f'did rename {sfinfo.path.name} -> {dest.name}'
        sfinfo.path, sfinfo.filename = dest, dest.relative_to(sfinfo.root_folder)
        sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=msg))

    def _is_file_corrupt(self, sfinfo: SfInfo) -> bool:
        """
        checks if the file throws any error while opening or playing. error loging is added to the SfInfo class
        if the file fails completely, it's moved to _FAILED. Only return True if there are major errors
        :returns True if file is readable
        :param sfinfo the metadata of the file to analyse
        """
        # check stream integrity # TODO file integrity for other files than Audio/Video/IMAGE
        # returns False if bin is soffice or empty string (means no integrity tests)

        # in strict mode, filter files that are not in the policies
        if self.mode.STRICT:
            if sfinfo.processed_as not in self.policies.keys():
                return False

        pbin = ""
        if sfinfo.processed_as in self.policies:
            pbin = self.policies[sfinfo.processed_as]["bin"]
        # select bin out of mimetype if not specified in policies
        if pbin == "" and sfinfo.matches[0]["mime"] != "":
            if sfinfo.matches[0]["mime"].split("/")[0] in ["image", "audio", "video"]:
                mime = sfinfo.matches[0]["mime"].split("/")[0]
                pbin = Bin.MAGICK if mime == "image" else Bin.FFMPEG
                msg = f'bin not specified in policies, using {pbin} according to the file mimetype for integrity tests'
                sfinfo.processing_logs.append(LogMsg(name="filehandler", msg=msg))

        # get the specs and errors
        match pbin:
            case Bin.FFMPEG:
                error, warning, specs = Ffmpeg.is_corrupt(sfinfo, verbose=self.mode.VERBOSE)
                if specs and not sfinfo.media_info:
                    sfinfo.media_info.append(LogMsg(name=Bin.FFMPEG, msg=json.dumps(specs)))
                if warning:
                    sfinfo.processing_logs.append(LogMsg(name=Bin.FFMPEG, msg=warning))
                    # see if warning needs file to be re-encoded
                    if any([msg in warning for msg in ErrMsgReencode]):
                        sfinfo.processing_logs.append(LogMsg(name="filehandler", msg="re-encoding the file"))
                        sfinfo.status.pending = True
            case Bin.MAGICK:
                error, warning, specs = ImageMagick.is_corrupt(sfinfo, verbose=self.mode.VERBOSE)  # type: ignore
                if specs and not sfinfo.media_info:
                    sfinfo.media_info.append(LogMsg(name=Bin.MAGICK, msg=specs))  # type: ignore
                if warning:
                    sfinfo.processing_logs.append(LogMsg(name=Bin.MAGICK, msg=warning))
            case _:
                return False

        if error:
            self.log_tables.diagnostics_add(sfinfo, FileDiagnosticsMsg.ERROR)
            return True
        if warning:
            self.log_tables.diagnostics_add(sfinfo, FileDiagnosticsMsg.WARNING)
            return False
        return False

    def _has_valid_streams(self, sfinfo: SfInfo) -> bool:
        streams = Ffmpeg.media_info(sfinfo.path)
        if not streams:
            secho(f'\t{sfinfo.filename} throwing errors. consider to run script with flag -i [--integrity-tests]',
                  fg=colors.RED, bold=True)
            return True
        for stream in streams:
            if stream['codec_name'] not in ['h264', 'aac']:  # type: ignore
                return False
        return True

    def _load_policies(self, policies_path: Path) -> None:
        if policies_path.is_file():
            with open(policies_path, 'r') as f:
                self.policies = json.load(f)

        self._assert_policies()

    def _assert_policies(self) -> None:
        if not self.policies:
            print('could not load policies. please check filepath... exit')
            raise typer.Exit(1)
        for el in self.policies:
            if self.policies[el]['bin'] not in Bin:
                print(f'unknown bin {self.policies[el]["bin"]} found in policy {el} ... exit')
                raise typer.Exit(1)
            if not self.policies[el]['accepted']:
                for k in ["target_container", "processing_args", "expected", "remove_original"]:
                    if k not in self.policies[el].keys():
                        print(f'your policies missing field {k} in policy {el} ... exit')
                        raise typer.Exit(1)
                if ";" in self.policies[el]["processing_args"]:
                    print(f'; not allowed in processing_args. found in policy {el} ... exit')
                    raise typer.Exit(1)

    def _gen_policies(self, outpath: Path, blank: bool = False, extend: bool = False) -> None:
        """
        generates a policies.json with the default values stored in conf.policies.py with the encountered fileformats
        :param blank if set to True, it generates a blank policies.json
        :param extend if true, it expands the loaded policies with filetypes found in root_folder that are not in the
        loaded policies and writes out an updated policies.json
        """

        loaded_pol: dict[str, PolicyParams] | None = None
        if extend:
            loaded_pol = self.policies

        self.policies = generate_policies(outpath=outpath, ba=self.ba, fmt2ext=self.fmt2ext, strict=self.mode.STRICT,
                                          remove_original=self.mode.REMOVEORIGINAL, blank=blank, loaded_pol=loaded_pol)
        if not self.mode.QUIET:
            print_fileformats(puids=[el for el in self.ba.puid_unique], ba=self.ba, fmt2ext=self.fmt2ext,
                              policies=self.policies, strict=self.mode.STRICT)
            print(f'\nyou find the policies in {outpath}{JsonOutput.POLICIES}, if you want to modify them')
            if self.ba.blank:
                print(f'there are some non default policies: {[el for el in self.ba.blank]}\n',
                      f'-> you may adjust them (they are set as accepted now)')

    def _test_policies(self, puid: str | None = None) -> None:
        """test a policies.json with the smallest files of the directory. if puid is passed, it only tests the puid
        of the policies."""

        if puid:
            puids = [puid]
        else:
            puids = [puid for puid in self.ba.puid_unique if not self.policies[puid]['accepted']]

        if not puids:
            print(f'no files found that should be converted with given policies')
        else:
            print_fileformats(puids=[el for el in self.ba.puid_unique], ba=self.ba, fmt2ext=self.fmt2ext,
                              policies=self.policies, strict=self.mode.STRICT)
            print("\n --- testing policies with a sample from the directory ---")

            for puid in puids:
                # we want the smallest file first for running the test in FileHandler.test_conversion()
                self.ba.sort_puid_unique_by_size(puid)
                sample = self.ba.puid_unique[puid][0]
                secho(f'\n{puid}', fg=colors.YELLOW)
                test, duration, cmd = self.converter.run_test(sample)
                if test:
                    est_time = self.ba.total_size[puid] / test.derived_from.filesize * duration  # type:ignore
                    secho(f'{cmd}', fg=colors.GREEN, bold=True)
                    secho(f'\napplying the policies for this filetype would approximately take '
                          f'{int(est_time) / 60: .2f} min. You find the file with the log in {test.filename.parent}')

    def _load_sfinfos(self, root_folder: Path) -> None:

        # set path to log.json, use parent.stem of root_folder if it is a file
        logpath_root = f'{root_folder.parent}.{root_folder.stem}' if root_folder.is_file() else root_folder
        # if there is a log, try to read from there
        if Path(f'{logpath_root}{JsonOutput.LOG}').is_file():
            for metadata in json.loads(Path(f'{logpath_root}{JsonOutput.LOG}').read_text())["files"]:
                 self.stack.append(SfInfo(**metadata))
            # append the root path values
            for sfinfo in self.stack:
                if not sfinfo.status.removed:
                    sfinfo.set_processing_paths(root_folder, self.wdir)

                    # else scan the root_folder with pygfried
        if not self.stack:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True,) as prog:
                prog.add_task(description="analysing files with siegfried...", total=None)
                for f in root_folder.rglob("*"):
                    if f.is_file():
                        self.stack.append(SfInfo(**pygfried.identify(f'{f}', detailed=True)["files"][0]))  # type: ignore [arg-type]
                if root_folder.is_file():
                    self.stack.append(SfInfo(**pygfried.identify(f'{root_folder}', detailed=True)["files"][0]))  # type: ignore [arg-type]
            # append the path values, set sfinfo.filename relative to root_folder
            for sfinfo in self.stack:
                sfinfo.set_processing_paths(root_folder, self.wdir, initial=True)

        # run basic analytics
        self.ba = BasicAnalytics()
        for sfinfo in self.stack:
            if not (sfinfo.status.removed or sfinfo.dest):
                self.ba.append(sfinfo)
        print_siegfried_errors(ba=self.ba)
        if not self.mode.QUIET:
            print_duplicates(ba=self.ba)

    def _manage_policies(self, root_folder: Path, policies_path: Path | None = None, blank: bool = False,
                         extend: bool = False) -> None:

        if not policies_path and Path(f'{root_folder}{JsonOutput.POLICIES}').is_file():
            policies_path = Path(f'{root_folder}{JsonOutput.POLICIES}')
        # no default policies found or the blank option is given:
        # fallback: generate the policies with optional flag blank
        if not policies_path or blank:
            if not self.mode.QUIET:
                print("... generating policies")
            self._gen_policies(root_folder, blank=blank)
        # load the external passed policies with option -p (polices_path)
        else:
            if not self.mode.QUIET:
                print(f'... loading policies form {policies_path}')
            self._load_policies(policies_path)

        # expand a passed policies with the filetypes found in root_folder that are not yet in the policies
        if extend and policies_path:
            if not self.mode.QUIET:
                print(f'... updating the filetypes in policies {policies_path}')
            self._gen_policies(root_folder, extend=extend)

        # add policies to converter
        self.converter.policies = self.policies

    def integrity_tests(self, root_folder: Path | str | None = None) -> None:

        if not self.stack and root_folder:
            root_folder = Path(root_folder)
            self._set_working_dir(root_folder)
            self._load_sfinfos(root_folder)
            self._manage_policies(root_folder)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description="doing file integrity tests ...", total=None)
            for sfinfo in self.stack:
                if not (sfinfo.status.removed or sfinfo.dest):
                    self._integrity_test(sfinfo)

        if not self.mode.QUIET:
            print_diagnostic(log_tables=self.log_tables, verbose=self.mode.VERBOSE)

    def apply_policies(self) -> None:

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description="applying policies...", total=None)
            for sfinfo in self.stack:
                if not (sfinfo.status.removed or sfinfo.dest):
                    self._apply_policy(sfinfo)

    def convert(self) -> None:
        """convert files whose metadata status.pending is True"""

        pending: list[SfInfo] = []
        for sfinfo in self.stack:
            if sfinfo.status.pending:
                pending.append(sfinfo)

        if not pending:
            if not self.mode.QUIET:
                print('there was nothing to convert')
            return

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description="converting ...", total=None)
            for sfinfo in pending:
                conv_sfinfo, cmd = self.converter.convert(sfinfo)
                if conv_sfinfo:
                    msg = f'converted -> {sfinfo.wdir.stem}/{conv_sfinfo.filename.parent.name}/{conv_sfinfo.filename.name}'
                    sfinfo.processing_logs.append(LogMsg(name="filehandler", msg=msg))
                    conv_sfinfo.root_folder = sfinfo.root_folder
                    self.stack.append(conv_sfinfo)
                else:
                    lmsg = sfinfo.processing_logs.pop()
                    lmsg.msg += f'. cmd={cmd} '
                    self.log_tables.errors.append((lmsg, sfinfo))

    def remove_tmp(self, root_folder: Path, to_csv: bool = False) -> None:

        # move converted files from the working dir to its destination
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description=f'moving files from {self.wdir.stem} to {root_folder.stem}...', total=None)
            write_logs = self._move_tmp()

        # remove empty folders in working dir
        if self.wdir.is_dir():
            for path, _, _ in os.walk(self.wdir, topdown=False):
                if len(os.listdir(path)) == 0:
                    os.rmdir(path)
        if write_logs:
            self.write_logs(root_folder, to_csv)

    def _move_tmp(self) -> bool:

        write_logs: bool = False

        for sfinfo in self.stack:
            # if it has a dest, it needs to be moved
            if sfinfo.dest:
                write_logs = True
                # remove the original if its mentioned and flag it accordingly
                if self.policies[sfinfo.derived_from.processed_as]['remove_original'] or self.mode.REMOVEORIGINAL:  # type: ignore
                    derived_from = [sfi for sfi in self.stack if sfinfo.derived_from.filename == sfi.filename][0]  # type: ignore
                    if derived_from.path.is_file():
                        self._remove(derived_from)
                # create absolute filepath
                abs_dest = sfinfo.root_folder / sfinfo.dest / sfinfo.filename.name
                # append hash to filename if the path already exists
                if abs_dest.is_file():
                    abs_dest = Path(abs_dest.parent, f'{sfinfo.filename.stem}_{sfinfo.md5[:6]}{sfinfo.filename.suffix}')
                # if its converted with docker container but -r flag is executed outside of docker, change the path
                if not sfinfo.filename.is_file():
                    sfinfo.filename = sfinfo.root_folder.parent / sfinfo.filename.relative_to("/data")
                # move the file
                err, msg, cmd = Rsync.copy(sfinfo.filename, abs_dest)
                # check if the return status is true
                if not err:
                    # remove working dir
                    if sfinfo.filename.parent.is_dir():
                        shutil.rmtree(sfinfo.filename.parent)
                    # set relative path in sfinfo.filename, set flags
                    sfinfo.filename = sfinfo.dest / abs_dest.name
                    sfinfo.status.added = True
                    sfinfo.dest = None
                else:  # rsync failed
                    secho(cmd, fg=colors.RED, bold=True)
                    self.log_tables.errors.append((LogMsg(name='rsync', msg=msg), sfinfo))

        return write_logs

    def write_logs(self, root_folder: Path | str, to_csv: bool = False) -> None:

        logoutput = LogOutput(files=self.stack, errors=self.log_tables.dump_errors())
        with open(Path(f'{root_folder}{JsonOutput.LOG}'), "w") as f:
            f.write(logoutput.model_dump_json(indent=4, by_alias=True, exclude_none=True))

        if self.mode.VERBOSE:
            print_processing_errors(log_tables=self.log_tables)

        if to_csv:
            with open(f'{root_folder}.csv', "w") as f:
                w = csv.DictWriter(f, CSVFIELDS)
                w.writeheader()
                [w.writerow(sfinfo2csv(el)) for el in self.stack]
                #[w.writerow(el.model_dump(exclude={'derived_from', 'dest', 'errors', 'matches'}, by_alias=True))
                # for el in self.stack]

        exit(0)

    # default run, has a typer interface for the params in identify.py
    def run(self, root_folder: Path | str, tmp_dir: Path | None = None, integrity_tests: bool = True, apply: bool = True,
            remove_tmp: bool = True, convert: bool = False, policies_path: Path | None = None, blank: bool = False, extend: bool = False,
            test_puid: str | None = None, test_policies: bool = False, remove_original: bool = False, mode_strict: bool = False,
            mode_verbose: bool = True, mode_quiet: bool = True, to_csv: bool = False) -> None:

        root_folder = Path(root_folder)
        # configure working dir
        self._set_working_dir(root_folder, tmp_dir)
        # set the mode
        mode = Mode(REMOVEORIGINAL=remove_original, STRICT=mode_strict, VERBOSE=mode_verbose, QUIET=mode_quiet)
        self.mode = mode
        # generate a list of SfInfo objects out of the target folder
        self._load_sfinfos(root_folder)
        # set root_folder if it is a file
        root_folder = Path(f'{root_folder.parent}.{root_folder.stem}') if root_folder.is_file() else root_folder
        # generate policies
        self._manage_policies(root_folder, policies_path, blank, extend)
        # convert caveat
        if convert:
            self.convert()
        # remove tmp caveat
        if remove_tmp:
            self.remove_tmp(root_folder, to_csv)
        # file integrity tests
        if integrity_tests:
            self.integrity_tests()
        # policies testing
        if test_puid:
            self._test_policies(puid=test_puid)
        if test_policies:
            self._test_policies()
        # apply policies
        if apply:
            self.apply_policies()
            self.convert()
        # remove tmp files
        if remove_tmp:
            self.remove_tmp(root_folder, to_csv)
        # write logs (if not called within remove_tmp)
        self.write_logs(root_folder, to_csv)

    def _set_working_dir(self, root_folder: Path, tmp_dir: Path | None = None) -> Path:
        if root_folder.is_file():
            root_folder = root_folder.parent
        if not tmp_dir and not PathsConfig.WDIR.__contains__("/"):
            self.wdir = Path(f'{root_folder}_{PathsConfig.WDIR}')
            return self.wdir
        if tmp_dir:
            self.wdir = Path(tmp_dir)
        if not self.wdir.is_absolute():
            self.wdir = Path.home() / self.wdir
        # avoid the home directory
        if str(self.wdir) == str(Path.home()):
            self.wdir = Path(self.wdir / f'fileidentification_{datetime.now().strftime("%Y%m%d")}')
            print(f'working dir set to {self.wdir} - not using home')
        return self.wdir


class FileConverter:

    def __init__(self) -> None:
        self.policies: dict[str, Any] = {}
        if platform.system() == LibreOfficePath.Linux.name:
            self.soffice = LibreOfficePath.Linux
        else:
            self.soffice = LibreOfficePath.Darwin

    @staticmethod
    def _add_media_info(sfinfo: SfInfo, _bin: str) -> None:
        match _bin:
            case Bin.FFMPEG:
                streams = Ffmpeg.media_info(sfinfo.filename)
                sfinfo.media_info.append(LogMsg(name="ffmpeg", msg=json.dumps(streams)))
            case Bin.MAGICK:
                sfinfo.media_info.append(LogMsg(name="imagemagick", msg=ImageMagick.media_info(sfinfo.filename)))
            case _:
                pass

    @staticmethod
    def verify(target: Path, sfinfo: SfInfo, expected: list[str]) -> SfInfo | None:
        """analyse the created file with siegfried, returns a SfInfo for the new file,
        :param sfinfo the metadata of the origin
        :param target the path to the converted file to analyse with siegfried
        :param expected the expected file format, to verify the conversion
        """
        target_sfinfo = None
        if target.is_file():
            # generate a SfInfo of the converted file
            target_sfinfo = SfInfo(**pygfried.identify(f'{target}', detailed=True)["files"][0]) # type:ignore [arg-type]
            # only add postprocessing information if conversion was successful
            if target_sfinfo.processed_as in expected:
                target_sfinfo.dest = sfinfo.filename.parent
                target_sfinfo.derived_from = sfinfo
                sfinfo.status.pending = False

            else:
                p_error = f' did expect {expected}, got {target_sfinfo.processed_as} instead'
                sfinfo.processing_logs.append(
                    LogMsg(name='filehandler', msg=f'{FileProcessingMsg.NOTEXPECTEDFMT}' + p_error))
                secho(f'\tERROR: {p_error} when converting {sfinfo.filename} to {target}', fg=colors.YELLOW, bold=True)
                target_sfinfo = None

        else:
            # conversion error, nothing to analyse
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileProcessingMsg.CONVFAILED}'))
            secho(f'\tERROR failed to convert {sfinfo.filename} to {target}', fg=colors.RED, bold=True)

        return target_sfinfo

    # file migration
    def convert(self, sfinfo: SfInfo) -> tuple[SfInfo | None, list[str]]:
        """
        convert a file, returns the metadata of the converted file as SfInfo
        :param sfinfo the metadata of the file to convert
        """

        args = self.policies[sfinfo.processed_as]  # type: ignore

        target_path, cmd, logfile_path = Con.convert(sfinfo, args, self.soffice)

        # replace abs path in logs, add name
        processing_log = None
        logtext = logfile_path.read_text().replace(f'{sfinfo.root_folder}/', "").replace(f'{sfinfo.wdir}/', "")
        if logtext != "":
            processing_log = LogMsg(name=f'{args["bin"]}', msg=logtext)

        # create an SfInfo for target and verify output, add codec and processing logs
        target_sfinfo = self.verify(target_path, sfinfo, args['expected'])
        if target_sfinfo:
            self._add_media_info(target_sfinfo, args['bin'])
            if processing_log:
                target_sfinfo.processing_logs.append(processing_log)

        return target_sfinfo, [cmd]

    def run_test(self, sfinfo: SfInfo) -> tuple[SfInfo | None, float, list[str]]:

        sfinfo.wdir = sfinfo.wdir / PathsConfig.TEST
        start = time()
        test, cmd = self.convert(sfinfo)
        duration = time() - start
        return test, duration, cmd
