from __future__ import annotations
import os
import platform
import shutil
import json
import csv
import typer
from time import time
from datetime import datetime
from typer import secho, colors
from rich.progress import Progress, SpinnerColumn, TextColumn
from enum import StrEnum
from pathlib import Path
from dataclasses import dataclass, field, fields
from typing import Union
from fileidentification.wrappers.wrappers import Siegfried as Sf, Ffmpeg, Converter as Con, ImageMagick, Rsync
from fileidentification.wrappers import homebrew_packeges
from fileidentification.parser.parser import SFParser
from fileidentification.output import RenderTables
from fileidentification.helpers import get_hash
from fileidentification.conf.settings import (PathsConfig, LibreOfficePath, FileDiagnosticsMsg, PolicyMsg, FileProcessingMsg,
                                              JsonOutput, Bin, ChangeLogErr)
from fileidentification.conf.models import SfInfo, BasicAnalytics, LogTables, LogMsg
from fileidentification.conf.policies import PoliciesGenerator
from fileidentification.conf.policies import systemfiles


@dataclass
class Mode:
    """the different modes for the filehandling class.
    REMOVEORIGINAL: do not remove the original files of the files that got converted
    VERBOSE: do verbose analysis of video and image files
    STRICT: move files that are not listed in policies to FAILED istead of skipping them
    QUIET: just print warnings and errors"""
    REMOVEORIGINAL: bool = False
    VERBOSE: bool = False
    STRICT: bool = False
    QUIET: bool = False


@dataclass
class FileHandler:
    """
    It can create, verify and apply policies, test the integrity of the files and convert them (with FileConverter) and
    move and remove tmp files.
    """

    fmt2ext: dict = field(default_factory=dict)
    policies: dict = field(default_factory=dict)
    log_tables: LogTables = field(default_factory=LogTables)
    ba: BasicAnalytics = None
    stack: list[SfInfo] = field(default_factory=list)
    mode: Mode = field(default_factory=Mode)

    def __post_init__(self):
        with open(PathsConfig.FMT2EXT, 'r') as f:
            self.fmt2ext = json.load(f)
        if not self.mode:
            self.mode = Mode()
        # see if bin are installed
        homebrew_packeges.check()

    def _integrity_test(self, sfinfo: SfInfo):

        puid = sfinfo.processed_as
        if not puid:
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileProcessingMsg.PUIDFAIL} for {sfinfo.filename}'))
            self.log_tables.errors.append((sfinfo.processing_logs[-1], sfinfo))
            self._remove(sfinfo)
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

        # check if the file throws any errors while open/processing it with the respective bin
        if self._is_file_corrupt(sfinfo):
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileDiagnosticsMsg.ERROR}'))
            self._remove(sfinfo)
            return

        # case where there is an extension missmatch, rename the file if there is a unique ext
        if sfinfo.matches[0].warning == FileDiagnosticsMsg.EXTMISMATCH:
            if len(self.fmt2ext[puid]['file_extensions']) == 1:
                ext = "." + self.fmt2ext[puid]['file_extensions'][-1]
                self._rename(sfinfo, ext)
            else:
                msg = f'expecting one of the following ext: {[el for el in self.fmt2ext[puid]['file_extensions']]}'
                sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=msg))
                secho(f'WARNING: you should manually rename {sfinfo.filename}\n{sfinfo.processing_logs}', fg=colors.YELLOW)
            self.log_tables.diagnostics_add(sfinfo, FileDiagnosticsMsg.EXTMISMATCH)

    def _apply_policy(self, sfinfo: SfInfo) -> None:

        puid = sfinfo.processed_as
        if not puid:
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

    def _remove(self, sfinfo: SfInfo):
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
        self.ba.puid_unique[sfinfo.processed_as].remove(sfinfo)

    def _rename(self, sfinfo: SfInfo, ext: str):
        dest = sfinfo.path.with_suffix(ext)
        # if a file with same name and extension already there, append file hash to name
        if sfinfo.path.with_suffix(ext).is_file():
            dest = sfinfo.path.parent / f'{sfinfo.path.stem}_{sfinfo.filehash[:6]}{ext}'
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

        # get the specs and errors
        match self.policies[sfinfo.processed_as]["bin"]:
            case Bin.FFMPEG:
                error, warning, specs = Ffmpeg.is_corrupt(sfinfo, verbose=self.mode.VERBOSE)
                if specs and not sfinfo.codec_info:
                    sfinfo.codec_info.append(LogMsg(name=Bin.FFMPEG, msg=json.dumps(specs)))
                if warning:
                    sfinfo.processing_logs.append(LogMsg(name=Bin.FFMPEG, msg=warning))
            case Bin.MAGICK | Bin.INCSCAPE:
                error, warning, specs = ImageMagick.is_corrupt(sfinfo, verbose=self.mode.VERBOSE)
                if specs and not sfinfo.codec_info:
                    sfinfo.codec_info.append(LogMsg(name=Bin.MAGICK, msg=specs))
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
        streams = Ffmpeg.codec_info(sfinfo.path)
        if not streams:
            secho(f'\t{sfinfo.filename} throwing errors. consider to run script with flag -i [--integrity-tests]',
                  fg=colors.RED, bold=True)
            return True
        for stream in streams:
            if stream['codec_name'] not in ['h264', 'aac']:
                return False
            return True

    def _load_policies(self, policies_path: Path):
        if policies_path.is_file():
            with open(policies_path, 'r') as f:
                self.policies = json.load(f)

        self._assert_policies()

    def _assert_policies(self):
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

    def _gen_policies(self, root_folder: Path, blank: bool = False, extend: str = None) -> None:
        """
        generates a policies.json with the default values stored in conf.policies.py with the encountered fileformats (they
        are passed with a list of SfInfos. this is done by loading the sfinfo values into an BasicAnalytics table.
        returns the path of the policies.json
        :param root_folder the directory with the files to generate a default policies file
        :param blank if set to True, it generates a blank policies.json
        :param extend if true, it expands the loaded policies with filetypes found in root_folder that are not in the
        loaded policies and writes out an updated policies.json
        """

        if extend:
            name = extend
            self.ba.presets = {}
            extend = self.policies
            [self.ba.presets.update({k: name}) for k in self.policies]

        pol_gen = PoliciesGenerator(fmt2ext=self.fmt2ext)
        self.policies, self.ba = pol_gen.gen_policies(root_folder, ba=self.ba, strict=self.mode.STRICT,
                                                      remove_original=self.mode.REMOVEORIGINAL, blank=blank, extend=extend)
        if not self.mode.QUIET:
            RenderTables.print_fileformats(fh=self, puids=[el for el in self.ba.puid_unique])
            print(f'\nyou find the policies in {root_folder}_policies.json, if you want to modify them')
            if self.ba.blank:
                print(f'there are some non default policies: {[el for el in self.ba.blank]}\n',
                      f'-> you may adjust them (they are set as accepted now)')

    def _test_policies(self, puid: str = None) -> None:
        """test a policies.json with the smallest files of the directory. if puid is passed, it only tests the puid
        of the policies."""

        if puid:
            puids = [puid]
        else:
            puids = [puid for puid in self.ba.puid_unique if not self.policies[puid]['accepted']]

        if not puids:
            print(f'no files found that should be converted with given policies')
        else:
            RenderTables.print_fileformats(fh=self, puids=puids)
            print("\n --- testing policies with a sample from the directory ---")

            test_conv = FileConverter(policies=self.policies)

            for puid in puids:
                # we want the smallest file first for running the test in FileHandler.test_conversion()
                self.ba.puid_unique[puid] = self.ba.sort_by_filesize(self.ba.puid_unique[puid])
                sample = self.ba.puid_unique[puid][0]
                secho(f'\n{puid}', fg=colors.YELLOW)
                test, duration, cmd = test_conv.run_test(sample)
                if test:
                    est_time = self.ba.total_size[puid] / test.derived_from.filesize * duration
                    secho(f'{cmd}', fg=colors.GREEN, bold=True)
                    secho(f'\napplying the policies for this filetype would approximately take '
                          f'{int(est_time) / 60: .2f} min. You find the file with the log in {test.filename.parent}')

    def _load_sfinfos(self, root_folder: Path, wdir: Path):

        # set path to log.json, use parent.stem of root_folder if it is a file
        logpath_root = f'{root_folder.parent}.{root_folder.stem}' if root_folder.is_file() else root_folder
        # if there is a log, try to read from there
        if Path(f'{logpath_root}{JsonOutput.LOG}').is_file():
            self.stack = Postprocessor.parse_log(logpath_root)
            # append the directories values
            [sfinfo.set_processing_paths(root_folder, wdir) for sfinfo in self.stack if not sfinfo.status.removed]

        # else scan the root_folder with siegfried
        if not self.stack:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True,) as prog:
                prog.add_task(description="analysing files with siegfried...", total=None)
                sfoutput = Sf.analyse(root_folder)
            # get the json output from siegfried and parse it to SfInfo
            [self.stack.append(SFParser.gen_sfinfo(metadata)) for metadata in sfoutput]
            # append the directories values, set sfinfo.filename relative to root_folder
            [sfinfo.set_processing_paths(root_folder, wdir, initial=True) for sfinfo in self.stack]

        # run basic analytics
        self.ba = BasicAnalytics(fmt2ext=self.fmt2ext)
        [self.ba.append(sfinfo) for sfinfo in self.stack if not (sfinfo.status.removed or sfinfo.dest)]
        if self.mode.VERBOSE:
            RenderTables.print_siegfried_errors(self)

    def _manage_policies(self, root_folder: Path, policies_path: Path = None, blank=False, extend=False):

        if not policies_path and Path(f'{root_folder}{JsonOutput.POLICIES}').is_file():
            policies_path = Path(f'{root_folder}{JsonOutput.POLICIES}')
        # no default policies found or the blank option is given:
        # fallback: generate the policies with optional flag blank
        if not policies_path or blank:
            if not self.mode.QUIET:
                print("... generating policies")
            self._gen_policies(root_folder, blank)
        # load the external passed policies with option -p (polices_path)
        else:
            if not self.mode.QUIET:
                print(f'... loading policies form {policies_path}')
            self._load_policies(policies_path)

        # expand a passed policies with the filetypes found in root_folder that are not yet in the policies
        if extend:
            if not self.mode.QUIET:
                print(f'... updating the filetypes in policies {policies_path}')
            self._gen_policies(root_folder, extend=policies_path.stem)

    def integrity_tests(self, root_folder: Path | str = None):

        if not self.stack and root_folder:
            root_folder = Path(root_folder)
            wdir = self._set_working_dir(root_folder)
            self._load_sfinfos(root_folder, wdir)
            self._manage_policies(root_folder)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description="doing file integrity tests ...", total=None)
            [self._integrity_test(sfinfo) for sfinfo in self.stack if not (sfinfo.status.removed or sfinfo.dest)]

        if not self.mode.QUIET:
            RenderTables.print_diagnostic_table(self)

    def apply_policies(self):

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description="applying policies...", total=None)
            [self._apply_policy(sfinfo) for sfinfo in self.stack if not (sfinfo.status.removed or sfinfo.dest)]

    def convert(self) -> None:
        """convert files whose metadata status.pending is True"""
        fc = FileConverter(policies=self.policies)

        pending: list[SfInfo] = []
        [pending.append(sfinfo) for sfinfo in self.stack if sfinfo.status.pending]

        if not pending:
            if not self.mode.QUIET:
                print('there was nothing to convert')
            return

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description="converting ...", total=None)
            for sfinfo in pending:
                conv_sfinfo, _ = fc.convert(sfinfo)
                if conv_sfinfo:
                    msg = f'converted -> {conv_sfinfo.filename.parent.stem}/{conv_sfinfo.filename.name}'
                    sfinfo.processing_logs.append(LogMsg(name="filehandler", msg=msg))
                    conv_sfinfo.root_folder = sfinfo.root_folder
                    self.stack.append(conv_sfinfo)
                else:
                    self.log_tables.errors.append((sfinfo.processing_logs.pop(), sfinfo))

    def remove_tmp(self, root_folder: Path, wdir: Path, to_csv=False):

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description=f'moving files from {wdir.stem} to {root_folder.stem}...', total=None)
            write_logs = self._move_tmp()

        # remove empty folders in wdir
        for path, _, _ in os.walk(wdir, topdown=False):
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
                if self.policies[sfinfo.derived_from.processed_as]['remove_original'] or self.mode.REMOVEORIGINAL:
                    derived_from = [sfi for sfi in self.stack if sfinfo.derived_from.filename == sfi.filename][0]
                    if derived_from.path.is_file():
                        self._remove(derived_from)
                # create absolute filepath
                dest_abs = sfinfo.root_folder / sfinfo.dest / sfinfo.filename.name
                # append hash to filename if the path already exists
                if dest_abs.is_file():
                    dest_abs = Path(dest_abs.parent, f'{sfinfo.filename.stem}_{sfinfo.filehash[:6]}{sfinfo.filename.suffix}')
                # move the file
                err, msg, cmd = Rsync.copy(sfinfo.filename, dest_abs)
                # check if the return status is true
                if not err:
                    # remove working dir
                    if sfinfo.filename.parent.is_dir():
                        shutil.rmtree(sfinfo.filename.parent)
                    # set relative path in sfinfo.filename, set flags
                    sfinfo.processing_logs.append(LogMsg(name='rsync', msg=msg))
                    sfinfo.filename = sfinfo.dest / dest_abs.name
                    sfinfo.status.added = True
                    sfinfo.dest = None
                else:  # rsync failed
                    secho(cmd, fg=colors.RED, bold=True)
                    self.log_tables.errors.append((LogMsg(name='rsync', msg=msg), sfinfo))

        return write_logs

    def write_logs(self, root_folder: Path | str, to_csv=False):

        Postprocessor.dump_json(self.stack, root_folder, JsonOutput.LOG, sha256=True)
        Postprocessor.dump_json(self.log_tables.dump_errors(), root_folder, JsonOutput.FAILED)
        if self.mode.VERBOSE:
            RenderTables.print_processing_errors(fh=self)
        if to_csv:
            Postprocessor.write_csv(self.stack, root_folder)
        # exit
        exit(0)

    @staticmethod
    def _save_policies_from(root_folder):
        if not Path(f'{root_folder}{JsonOutput.POLICIES}').is_file():
            print('you have to generate policies first, please run\n')
            print(f'indentify.py {root_folder}')
            raise typer.Exit(1)
        presetname = typer.prompt("name for the preset:")
        if not Path(PathsConfig.PRESETS).is_dir():
            os.mkdir(PathsConfig.PRESETS)
        shutil.copy(f'{root_folder}{JsonOutput.POLICIES}', Path(PathsConfig.PRESETS).joinpath(presetname))
        print(f'policies saved in {PathsConfig.PRESETS}/{presetname}')
        raise typer.Exit()

    # default run, has a typer interface for the params in identify.py
    def run(self, root_folder: Path | str, tmp_dir: Path = None, integrity_tests: bool = True, apply: bool = True,
            remove_tmp: bool = True, convert: bool = False, policies_path: Path = None, blank: bool = False, extend: bool = False,
            test_puid: str = None, test_policies: bool = False, remove_original: bool = False, mode_strict: bool = False,
            mode_verbose: bool = True, mode_quiet: bool = True, save_policies: bool = False, to_csv: bool = False):
        # check path
        root_folder = Path(root_folder)
        # configure working dir
        wdir = self._set_working_dir(root_folder, tmp_dir)
        # set the mode
        mode = Mode(REMOVEORIGINAL=remove_original, STRICT=mode_strict, VERBOSE=mode_verbose, QUIET=mode_quiet)
        self.mode = mode
        # save policies caveat
        if save_policies:
            self._save_policies_from(root_folder)
        # generate a list of SfInfo objects out of the target folder generate policies
        self._load_sfinfos(root_folder, wdir)
        # set root_folder if it is a file
        root_folder = f'{root_folder.parent}.{root_folder.stem}' if root_folder.is_file() else root_folder
        # generate policies
        self._manage_policies(root_folder, policies_path, blank, extend)
        # convert caveat
        if convert:
            self.convert()
        # remove tmp caveat
        if remove_tmp:
            self.remove_tmp(root_folder, wdir, to_csv)
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
            self.remove_tmp(root_folder, wdir, to_csv)
        # write logs (if not called within remove_tmp)
        self.write_logs(root_folder, to_csv)

    def _set_working_dir(self, root_folder: Path, tmp_dir: Path = None) -> Path:
        if root_folder.is_file():
            root_folder = root_folder.parent
        if not tmp_dir and not PathsConfig.WDIR.__contains__("/"):
            return Path(f'{root_folder}_{PathsConfig.WDIR}')
        wdir = Path(PathsConfig.WDIR)
        if tmp_dir:
            wdir = tmp_dir
        if not wdir.is_absolute():
            wdir = Path.home() / wdir
        # avoid the home directory
        if str(wdir) == str(Path.home()):
            wdir = Path(wdir / f'fileidentification{datetime.now().strftime("%Y%m%d")}')
            print(f'working dir set to {wdir} - not using home')
        return wdir


class FileConverter:

    def __init__(self, policies):
        self.policies: dict = policies
        if platform.system() == LibreOfficePath.Linux.name:
            self.soffice = Path(LibreOfficePath.Linux)
        else:
            self.soffice = Path(LibreOfficePath.Darwin)

    @staticmethod
    def _add_codec_info(sfinfo: SfInfo, _bin: str):
        match _bin:
            case Bin.FFMPEG:
                streams = Ffmpeg.codec_info(sfinfo.filename)
                sfinfo.codec_info.append(LogMsg(name="ffmpeg", msg=json.dumps(streams)))
            case Bin.MAGICK | Bin.INCSCAPE:
                sfinfo.codec_info.append(LogMsg(name="imagemagick", msg=ImageMagick.codec_info(sfinfo.filename)))
            case _:
                pass

    @staticmethod
    def verify(target: Path, sfinfo: SfInfo, expected: list) -> SfInfo | None:
        """analyse the created file with siegfried, returns a SfInfo for the new file,
        :param sfinfo the metadata of the origin
        :param target the path to the converted file to analyse with siegfried
        :param expected the expected file format, to verify the conversion
        """
        target_sfinfo = None
        if target.is_file():
            # generate a SfInfo of the converted file
            target_sfinfo = SFParser.gen_sfinfo(Sf.analyse(target)[0])
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
    def convert(self, sfinfo: SfInfo) -> tuple[SfInfo, list]:
        """
        convert a file, returns the metadata of the converted file as SfInfo
        :param sfinfo the metadata of the file to convert, updated if successfully converted
        """

        args = self.policies[sfinfo.processed_as]

        target_path, cmd, logfile_path = Con.convert(sfinfo, args, self.soffice)

        # replace abs path in logs, add name
        processing_log = None
        logtext = logfile_path.read_text().replace(f'{sfinfo.root_folder}/', "").replace(f'{sfinfo.wdir}/', "")
        if logtext != "":
            processing_log = LogMsg(name=f'{args["bin"]}', msg=logtext)

        # create an SfInfo for target and verify output, add codec and processing logs
        target_sfinfo = self.verify(target_path, sfinfo, args['expected'])
        if target_sfinfo:
            self._add_codec_info(target_sfinfo, args['bin'])
            if processing_log:
                target_sfinfo.processing_logs.append(processing_log)

        return target_sfinfo, [cmd]

    def run_test(self, sfinfo: SfInfo) -> tuple[SfInfo, float, list]:

        sfinfo.wdir = sfinfo.wdir / PathsConfig.TEST
        start = time()
        test, cmd = self.convert(sfinfo)
        duration = time() - start
        return test, duration, cmd


class Postprocessor:

    @staticmethod
    def dump_json(listitems: list, path: Path, filename: Union[StrEnum, str], sha256: bool = False) -> None:
        """writes a list of dataclass object to a file. the objects need a method as_dict()

        :param listitems: the list containing the dataclass objects
        :param path: to write the file to
        :param filename: of the file, preferably a StrEnum
        :param sha256: if set to True, it writes the hash of the file to filename.sha256"""

        if not listitems:
            return
        jsonout: dict = {}
        outfile = f'{path}{filename}'
        [jsonout.update({f'{el.filename}': el.as_dict()}) for el in listitems]
        with open(outfile, 'w') as f:
            json.dump(jsonout, f, indent=4, ensure_ascii=False)
        if sha256:
            Path(f'{outfile}.sha256').write_text(get_hash(outfile))

    @staticmethod
    def _verify_file(file: Path) -> Path | str:
        """verifies file with hash"""
        if Path(f'{file}.sha256').is_file():
            sha256 = Path(f'{file}.sha256').read_text()
            if sha256 == get_hash(file):
                return file
            return ChangeLogErr.MODIFIED
        return ChangeLogErr.NOHASH

    @staticmethod
    def parse_log(root_folder: Path) -> list[SfInfo]:

        log_path = Postprocessor._verify_file(Path(f'{root_folder}{JsonOutput.LOG}'))
        stack: list[SfInfo] = []
        if isinstance(log_path, Path):
            stack.extend(SFParser.read_changelog(log_path))
        else:
            secho(f'ERROR: {log_path}', fg=colors.RED, bold=True)
            bkp = f'{root_folder}_{datetime.now().strftime("%Y%m%d_%H%M%S")}{JsonOutput.LOG}'
            shutil.copy(f'{root_folder}{JsonOutput.LOG}', bkp)
            secho(f'did backup the file as {bkp}')
            rescan = typer.confirm("Do you want to rescan the directory?")
            if not rescan:
                raise typer.Exit()
        return stack

    @staticmethod
    def write_csv(items: list[SfInfo], root_folder: Path):
        outfile = f'{root_folder}.csv'
        with open(outfile, 'w') as f:
            flds = [fld.name for fld in fields(SfInfo) if fld.name not in ['matches', 'tmp_file', 'path', 'root_folder',
                                                                           'wdir', 'codec_info']]
            w = csv.DictWriter(f, flds)
            w.writeheader()
            w.writerows([Postprocessor.to_csv(sfi) for sfi in items])
        # mapping
        jsonout: dict = {}
        [jsonout.update({f'{sfi.derived_from.filename}': f'{sfi.filename}'}) for sfi in items if sfi.derived_from]
        if jsonout:
            with open(f'{root_folder}.mapping.json', 'w') as f:
                json.dump(jsonout, f, indent=4, ensure_ascii=False)

    @staticmethod
    def to_csv(sfinfo: SfInfo) -> dict:
        res = {"filename": f'{sfinfo.filename}',
               "filesize": sfinfo.filesize,
               "modified": sfinfo.modified,
               "errors": sfinfo.errors,
               "filehash": sfinfo.filehash}
        if sfinfo.status.pending:
            res.update({"status": "pending"})
        if sfinfo.status.added:
            res.update({"status": "added"})
        if sfinfo.status.removed:
            res.update({"status": "removed"})
        if sfinfo.processed_as:
            res['processed_as'] = sfinfo.processed_as
        if sfinfo.processing_logs:
            res['processing_logs'] = " ; ".join([el.msg for el in sfinfo.processing_logs if el.name == "filehandler"])
        if sfinfo.derived_from:
            res['derived_from'] = sfinfo.derived_from.filename
        return res
