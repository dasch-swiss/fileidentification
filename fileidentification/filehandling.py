from __future__ import annotations
import os
import platform
import shutil
import json
import typer
from time import time
from typer import secho, colors
from rich.progress import Progress, SpinnerColumn, TextColumn
from enum import StrEnum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Union
from fileidentification.wrappers.wrappers import Siegfried as Sf, Ffmpeg, Converter as Con, ImageMagick, Rsync
from fileidentification.parser.parser import SFParser
from fileidentification.output import RenderTables
from fileidentification.helpers import get_hash
from conf.settings import (PathsConfig, LibreOfficePath, FileDiagnosticsMsg, PolicyMsg, FileProcessingErr,
                           FileOutput, Bin, ChangeLogErr)
from conf.models import SfInfo, CleanUpTable, BasicAnalytics, LogTables, LogMsg
from conf.policies import PoliciesGenerator
from conf.policies import systemfiles


@dataclass
class Mode:
    """the different modes for the filehandling class.
    DELETEORIGINAL: do not delete the original files of the files that got converted
    VERBOSE: do verbose analysis of video and image files
    STRICT: move files that are not listed in policies to FAILED istead of skipping them
    QUIET: just print warnings and errors"""
    DELETEORIGINAL: bool = False
    VERBOSE: bool = False
    STRICT: bool = False
    QUIET: bool = False


@dataclass
class FileHandler:
    """
    It can create, verify and apply policies. convert files (with FileConverter) and cleanup
    """

    fmt2ext: dict = field(default_factory=dict)
    policies: dict = field(default_factory=dict)
    log_tables: LogTables = field(default_factory=LogTables)
    ba: BasicAnalytics = None
    pinned2log: list[SfInfo] = field(default_factory=list)
    pinned2convert: list[SfInfo] = field(default_factory=list)
    sfinfos: list[SfInfo] = field(default_factory=list)
    # processing states
    mode: Mode = field(default_factory=Mode)

    def __post_init__(self):
        with open(PathsConfig.FMT2EXT, 'r') as f:
            self.fmt2ext = json.load(f)
        if not self.mode:
            self.mode = Mode()

    def _integrity_test(self, sfinfo: SfInfo) -> SfInfo | None:

        puid = sfinfo.processed_as
        if not puid:
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileProcessingErr.PUIDFAIL}'))
            self._move2failed(sfinfo)
            self.log_tables.processingerr.append(sfinfo)
            return

        if sfinfo.errors == FileDiagnosticsMsg.EMPTYSOURCE:
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileDiagnosticsMsg.EMPTYSOURCE}'))

            self.pinned2log.append(Postprocessor.set_relativepath(sfinfo))
            self.log_tables.append2diagnostics(sfinfo, FileDiagnosticsMsg.EMPTYSOURCE)
            return

        # os specific files we do not care, eg .DS_store etc
        if puid in systemfiles:  # ['fmt/394']:
            # could also simply remove them
            # os.remove(sfinfo.filename)
            return

        # check if the file throws any errors while open/processing it with the respective bin
        if self._is_file_corrupt(sfinfo):
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileDiagnosticsMsg.ERROR}'))
            self._move2failed(sfinfo)
            return

        # case where there is an extension missmatch, rename the file if there is a unique ext
        if sfinfo.matches[0].warning == FileDiagnosticsMsg.EXTMISMATCH:
            if len(self.fmt2ext[puid]['file_extensions']) == 1:
                ext = "." + self.fmt2ext[puid]['file_extensions'][-1]
                self._rename(sfinfo, ext)
            else:
                msg = f'expecting one of the following ext: {[el for el in self.fmt2ext[puid]['file_extensions']]}'
                sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=msg))
                self.log_tables.append2diagnostics(sfinfo, FileDiagnosticsMsg.EXTMISMATCH)
                secho(f'WARNING: you should manually rename {sfinfo.filename}\n{sfinfo.processing_logs}', fg=colors.YELLOW)

        # file passed the integrity test
        self.sfinfos.append(sfinfo)

    def _apply_policy(self, sfinfo: SfInfo) -> None:

        puid = sfinfo.processed_as
        if not puid:
            return

        if puid not in self.policies:
            # in strict mode, move file
            if self.mode.STRICT:
                sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{PolicyMsg.NOTINPOLICIES}'))
                self.log_tables.append2policies(sfinfo, PolicyMsg.NOTINPOLICIES)
                self._move2failed(sfinfo)
                return
            # just flag it as skipped
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{PolicyMsg.SKIPPED}'))
            self.log_tables.append2policies(sfinfo, PolicyMsg.SKIPPED)
            return

        # case where file needs to be converted
        if not self.policies[puid]['accepted']:
            self.pinned2convert.append(sfinfo)
            return

        # check if mp4 has correct stream (i.e. h264 and aac)
        if puid in ['fmt/199']:
            if not self._has_valid_streams(sfinfo):
                self.pinned2convert.append(sfinfo)
                return

        # case where file is accepted as it is, all good, append it to passed if flag in policies is true
        if self.policies[puid]['accepted']:
            if "force_log" in self.policies[puid].keys() and self.policies[puid]['force_log']:
                self.pinned2log.append(Postprocessor.set_relativepath(sfinfo))
            return

    def _move2failed(self, sfinfo: SfInfo):
        dest = Path(f'{sfinfo.files_dir}{PathsConfig.FAILED}' / sfinfo.relative_path)
        if not dest.exists():
            os.makedirs(dest)
        rstatus, msg, cmd = Rsync.copy(sfinfo.filename, dest)
        sfinfo.processing_logs.append(LogMsg(name='rsync', msg=msg))
        # if there was an error, append to processing err tables
        if rstatus:
            secho(f'{FileProcessingErr.FAILEDMOVE} {cmd}', fg=colors.RED)
            self.log_tables.processingerr.append(sfinfo)
        else:
            os.remove(sfinfo.filename)
        self.pinned2log.append(Postprocessor.set_relativepath(sfinfo))
        self.ba.puid_unique[sfinfo.processed_as].remove(sfinfo)

    def _rename(self, sfinfo: SfInfo, ext: str):
        dest = sfinfo.filename.with_suffix(ext)
        # if a file with same name and extension already there, append file hash to name
        if Path(sfinfo.filename.with_suffix(ext)).is_file():
            dest = Path(sfinfo.files_dir / sfinfo.relative_path / f'{sfinfo.filename.stem}_{sfinfo.filehash}{ext}')
        msg = f'expecting {ext} : did rename {sfinfo.filename.stem} -> {dest}'
        os.rename(sfinfo.filename, dest)
        sfinfo.filename = dest
        sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=msg))
        self.log_tables.append2diagnostics(sfinfo, FileDiagnosticsMsg.EXTMISMATCH)

    def _is_file_corrupt(self, sfinfo: SfInfo) -> bool:
        """
        checks if the file throws any error while opening or playing. error loging is added to the SfInfo class
        if the file fails completely, it's moved to _FAILED. Only return True if there are major errors
        :returns True if file is readable
        :param sfinfo the metadata of the file to analyse
        """
        # check stream integrity # TODO file integrity for other files than Audio/Video/IMAGE
        # returns False if bin is soffice or empty string (means no integrity tests)

        # get the specs and errors
        match self.policies[sfinfo.processed_as]["bin"]:
            case Bin.FFMPEG:
                error, warning, specs = Ffmpeg.is_corrupt(sfinfo, verbose=self.mode.VERBOSE)
                if specs:
                    sfinfo.codec_info.append(LogMsg(name='ffmpeg', msg=specs))
                if warning:
                    sfinfo.processing_logs.append(LogMsg(name='ffmpeg', msg=warning))
            case Bin.MAGICK:
                error, warning, specs = ImageMagick.is_corrupt(sfinfo, verbose=self.mode.VERBOSE)
                if specs:
                    sfinfo.codec_info.append(LogMsg(name='imagemagick', msg=specs))
                if warning:
                    sfinfo.processing_logs.append(LogMsg(name='imagemagick', msg=warning))
            case _:
                return False

        if error:
            self.log_tables.append2diagnostics(sfinfo, FileDiagnosticsMsg.ERROR)
            return True
        if warning:
            self.log_tables.append2diagnostics(sfinfo, FileDiagnosticsMsg.WARNING)
            return False
        return False

    def _has_valid_streams(self, sfinfo: SfInfo) -> bool:
        streams = Ffmpeg.streams_as_json(sfinfo)
        if not streams:
            secho(f'{sfinfo.filename} throwing errors. consider to run folder with flag -i [--integrity-tests]', fg=colors.RED, bold=True)
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
                for k in ["target_container", "processing_args", "expected", "delete_original"]:
                    if k not in self.policies[el].keys():
                        print(f'your policies missing field {k} in policy {el} ... exit')
                        raise typer.Exit(1)
                if ";" in self.policies[el]["processing_args"]:
                    print(f'; not allowed in processing_args. found in policy {el} ... exit')
                    raise typer.Exit(1)

    @staticmethod
    def append_path_values(sfinfo: SfInfo, files_dir: Path, wdir: Path) -> SfInfo:
        if files_dir.is_file():
            files_dir = files_dir.parent
        sfinfo.relative_path = sfinfo.filename.parent.relative_to(files_dir)
        sfinfo.files_dir = files_dir
        sfinfo.wdir = wdir
        return sfinfo

    def _gen_default_policies(self, files_dir: Path, blank: bool = False, extend: str = None) -> None:
        """
        generates a policies.json with the default values stored in conf.policies.py with the encountered fileformats (they
        are passed with a list of SfInfos. this is done by loading the sfinfo values into an BasicAnalytics table. that
        table can generate policies among printing out some basic analytics.
        returns the path of the policies.json
        :param files_dir the directory with the files to generate a default policies file
        :param blank if set to True, it generates a blank policies.json
        :param extend if true, it expands the loaded policies with filetypes found in files_dir that are not in the
        loaded policies and writes out an updated policies.json
        """

        if extend:
            name = extend
            self.ba.presets = {}
            extend = self.policies
            [self.ba.presets.update({k: name}) for k in self.policies]

        pol_gen = PoliciesGenerator(fmt2ext=self.fmt2ext)
        self.policies, self.ba = pol_gen.gen_policies(files_dir, ba=self.ba, strict=self.mode.STRICT,
                                                      delete_original=self.mode.DELETEORIGINAL, blank=blank, extend=extend)
        if not self.mode.QUIET:
            RenderTables.print_fileformats(self, puids=[el for el in self.ba.puid_unique])
            print(f'\nyou find the policies in {files_dir}_policies.json, if you want to modify them')
            if self.ba.blank:
                print(f'there are some non default policies: {[el for el in self.ba.blank]}\n',
                      f'-> you may adjust them (they are set as accepted now)')

    def test_policies(self, files_dir: Path, wdir: Path, puid: str = None) -> None:
        """test a policies.json with the smallest files of the directory. if puid is passed, it only tests the puid
        of the policies."""

        if wdir.joinpath(PathsConfig.TEST).is_dir():
            shutil.rmtree(wdir.joinpath(PathsConfig.TEST))

        puids: list = []
        if puid:
            puids = [puid]
        else:
            if self.pinned2convert:
                puids = [puid for puid in self.ba.puid_unique if not self.policies[puid]['accepted']]

        if not puids:
            print(f'no files found in {files_dir} that should be converted with given policies')
        else:
            RenderTables.print_fileformats(self, puids=puids)
            print("\n --- testing policies with a sample from the directory ---")

            test_conv = FileConverter(policies=self.policies)

            for puid in puids:
                # we want the smallest file first for running the test in FileHandler.test_conversion()
                self.ba.puid_unique[puid] = self.ba.sort_by_filesize(self.ba.puid_unique[puid])
                sample = self.ba.puid_unique[puid][0]

                test, duration, cmd = test_conv.run_test(sample)
                print(f'\ntested with {cmd}')
                if test.cu_table:
                    if not self.mode.QUIET:
                        est_time = self.ba.total_size[puid] / test.derived_from.filesize * duration
                        print(f'\napplying the policies for this filetype would appoximatly take '
                              f'{int(est_time) / 60: .2f} min. You find the file with the log in {test.filename.parent}')

    def load_sfinfos(self, files_dir: Path, wdir: Path):

        if Path(f'{files_dir}{FileOutput.TMPSTATE}').is_file():
            self.sfinfos = Postprocessor.parse_changelog(files_dir, FileOutput.TMPSTATE)
            if self.sfinfos:
                os.remove(f'{files_dir}{FileOutput.TMPSTATE}')
                os.remove(f'{files_dir}{FileOutput.TMPSTATE}.sha256')

        if not self.sfinfos:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),transient=True,) as prog:
                prog.add_task(description="analysing files with siegfried...", total=None)
                sfoutput = Sf.analyse(files_dir)
            # get the json output from siegfried and parse it to SfInfo
            [self.sfinfos.append(SFParser.to_SfInfo(metadata)) for metadata in sfoutput]

        # append the directories values and run basic analytics
        [self.append_path_values(el, files_dir, wdir) for el in self.sfinfos]

        self.ba = BasicAnalytics(fmt2ext=self.fmt2ext)
        [self.ba.append(sfinfo) for sfinfo in self.sfinfos]
        RenderTables.print_siegfried_errors(self)

    def manage_policies(self, files_dir: Path, policies_path: Path, blank=False, extend=False):

        if not policies_path and Path(f'{files_dir}{FileOutput.POLICIES}').is_file():
            policies_path = Path(f'{files_dir}{FileOutput.POLICIES}')
        # no default policies found or the blank option is given:
        # fallback: generate the policies with optional flag blank
        if not policies_path or blank:
            if not self.mode.QUIET:
                print("... generating policies")
            self._gen_default_policies(files_dir, blank)
        # load the external passed policies with option -p (polices_path)
        else:
            if not self.mode.QUIET:
                print(f'... loading policies form {policies_path}')
            self._load_policies(policies_path)

        # expand a passed policies with the filetypes found in files_dir that are not yet in the policies
        if extend:
            if not self.mode.QUIET:
                print(f'... updating the filetypes in policies {policies_path}')
            self._gen_default_policies(files_dir, extend=policies_path.stem)

    def integrity_tests(self):

        stack = self.sfinfos
        self.sfinfos = []

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description="doing file integrity tests ...", total=None)
            [self._integrity_test(sfinfo) for sfinfo in stack]

        if not self.mode.QUIET:
            RenderTables.print_diagnostic_table(self)

    def apply_policies(self):

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description="applying policies...", total=None)
            [self._apply_policy(sfinfo) for sfinfo in self.sfinfos]

    def convert(self) -> list[SfInfo]:
        """convert files whose metadata are in a list of SfInfos"""
        fc = FileConverter(policies=self.policies)

        stack: list[SfInfo] = []

        if not self.pinned2convert:
            if not self.mode.QUIET:
                print('there was nothing to convert')
            stack.extend(self.pinned2log)
            return stack

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description="converting ...", total=None)
            for sfinfo in self.pinned2convert:
                sfinfo, _ = fc.convert(sfinfo)
                if sfinfo.cu_table:
                    stack.append(sfinfo)
                else:
                    self.log_tables.processingerr.append(sfinfo)

        return stack

    def cleanup(self, files_dir: Path, wdir: Path, stack = None):

        processed: list[SfInfo] = []
        if Path(f'{files_dir}{FileOutput.CHANGELOG}').is_file():
            processed = Postprocessor.parse_changelog(files_dir, FileOutput.CHANGELOG)
        processed.extend(self.pinned2log)

        if not stack:
            stack = Postprocessor.parse_changelog(files_dir, FileOutput.TMPSTATE)
            if stack:
                os.remove(f'{files_dir}{FileOutput.TMPSTATE}')
                os.remove(f'{files_dir}{FileOutput.TMPSTATE}.sha256')

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
            prog.add_task(description=f'moving files from {wdir.stem} to {files_dir.stem}...', total=None)
            stack, processed = self._cleanup(stack, processed, files_dir)
            stack.extend(processed)
            Postprocessor.dump_json(stack, files_dir, FileOutput.CHANGELOG, sha256=True)

        # remove empty folders in wdir
        for path, _, _ in os.walk(wdir, topdown=False):
            if len(os.listdir(path)) == 0:
                os.rmdir(path)

        if not self.mode.QUIET:
            print('did clean up')

    def _cleanup(self, stack: list[SfInfo], processed: list[SfInfo], files_dir: Path) -> tuple[list[SfInfo], list[SfInfo]]:

        for sfinfo in stack:
            if sfinfo.cu_table:
                tb = sfinfo.cu_table
                # delete the original if its mentioned, remove it from already processed
                if self.policies[sfinfo.derived_from.processed_as]['delete_original'] or self.mode.DELETEORIGINAL:
                    if Path(files_dir, sfinfo.derived_from.filename).is_file():
                        os.remove(Path(files_dir, sfinfo.derived_from.filename))
                    if processed:
                        [processed.remove(el) for el in processed if sfinfo.derived_from.filename == el.filename]
                # append hash to filename if the path already exists
                if Path(tb.dest / tb.filename.name).is_file():
                    tb.dest = tb.dest / f'{tb.filename.stem}_{sfinfo.filehash[:6]}{tb.filename.suffix}'
                # move the file
                rstatus, msg, cmd = Rsync.copy(tb.filename, tb.dest)
                # check if the return status is true
                if not rstatus:
                    # set relative path in sfinfo, remove cu_tables
                    sfinfo = Postprocessor.set_relativepath(sfinfo, tb.dest)
                    sfinfo.cu_table = None
                    # remove working dir
                    if tb.wdir.is_dir():
                        shutil.rmtree(tb.wdir)
                    sfinfo.processing_logs.append(LogMsg(name='rsync', msg=msg))
                    stack.append(sfinfo)
                else:  # rsync failed
                    secho(cmd, fg=colors.RED, bold=True)
                    sfinfo.processing_logs.append(LogMsg(name='rsync', msg=msg))
                    self.log_tables.processingerr.append(sfinfo)

        return stack, processed


class FileConverter:

    def __init__(self, policies):
        self.policies: dict = policies
        if platform.system() == LibreOfficePath.Linux.name:
            self.soffice = Path(LibreOfficePath.Linux)
        else:
            self.soffice = Path(LibreOfficePath.Darwin)

    @staticmethod
    def analyse_append_log(sfinfo: SfInfo, target: Path, processing_log: LogMsg | None, expected: list) \
            -> SfInfo:
        """analyse the created file with siegfried, returns a SfInfo for the new file,
        adds paths to CleanUpTable if successful

        :param sfinfo the metadata of the origin
        :param target the path to the converted file to analyse with siegfried
        :param processing_log the log during the conversion, added to SfInfo
        :param expected the expected fileformat, to verify the conversion
        """
        if target.is_file():
            # generate a SfInfo of the converted file
            target_sfinfo = SFParser.to_SfInfo(Sf.analyse(target)[0])
            if processing_log:
                target_sfinfo.processing_logs.append(processing_log)
            # only add postprocessing information if conversion was successful
            if target_sfinfo.processed_as not in expected:
                p_error = f' did expect {expected}, got {target_sfinfo.processed_as} instead'
                target_sfinfo.processing_logs.append(
                    LogMsg(name='filehandler', msg=f'{FileProcessingErr.NOTEXPECTEDFMT}' + p_error))
                secho(f'\nERROR: {p_error} when converting {sfinfo.filename} to {target}', fg=colors.YELLOW, bold=True)

            else:
                cu_table = CleanUpTable(
                    filename=target,
                    dest=Path(sfinfo.filename.parent),
                    wdir=target.parent,
                    relative_path=sfinfo.relative_path
                )
                target_sfinfo.cu_table = cu_table
            # set relative path in original file metadata, append it as derived_from to the converted one
            Postprocessor.set_relativepath(sfinfo)
            target_sfinfo.derived_from = sfinfo

        else:
            # conversion error, nothing to analyse
            target_sfinfo = sfinfo
            target_sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileProcessingErr.CONVFAILED}'))
            secho(f'\nERROR failed to convert {sfinfo.filename} to {target}', fg=colors.RED, bold=True)

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
        logtext = logfile_path.read_text().replace(f'{sfinfo.files_dir}/', "").replace(f'{sfinfo.wdir}/', "")
        if logtext != "":
            processing_log = LogMsg(name=f'{args["bin"]}', msg=logtext)

        # create an SfInfo for target - and if conversion succesfull append the original as parent to it
        # else return original with sfinfo.processing_error
        sfinfo = self.analyse_append_log(sfinfo, target_path, processing_log, args['expected'])

        return sfinfo, [cmd]

    def run_test(self, sfinfo: SfInfo) -> tuple[SfInfo, float, list]:
        sfinfo.wdir = Path(sfinfo.wdir / PathsConfig.TEST)
        start = time()
        test, cmd, = self.convert(sfinfo)
        duration = time() - start
        return test, duration, cmd


class Postprocessor:

    @staticmethod
    def set_relativepath(sfinfo: SfInfo, dest: Path = None) -> SfInfo:
        """replaces the absolute path with relative one in the filename of a SfInfo"""
        if sfinfo.relative_path:
            sfinfo.filename = sfinfo.relative_path / sfinfo.filename.name
        if sfinfo.cu_table:
            sfinfo.filename = sfinfo.cu_table.relative_path / sfinfo.filename.name
        if dest and dest.is_file():
            sfinfo.filename = sfinfo.cu_table.relative_path / dest.name
        return sfinfo

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
    def _verify_file(file: Path, sha256: bool = False) -> Path | str:
        """verifies file with hash"""
        if not file.is_file():
            return ChangeLogErr.NOFILE
        else:
            if not sha256:
                return file
            if sha256 and Path(f'{file}.sha256').is_file():
                sha256 = Path(f'{file}.sha256').read_text()
                if not sha256 == get_hash(file):
                    return ChangeLogErr.MODIFIED
                return file
            return ChangeLogErr.NOHASH

    @staticmethod
    def parse_changelog(files_dir: Path, filename: FileOutput) -> list[SfInfo]:

        changelog_path = Postprocessor._verify_file(Path(f'{files_dir}{filename}'), sha256=True)
        stack: list[SfInfo] = []
        if isinstance(changelog_path, Path):
            stack.extend(SFParser.read_changelog(changelog_path))
        else:
            secho(f'ERROR: {changelog_path} when accessing {files_dir}{filename}', fg=colors.RED, bold=True)
        return stack

    @staticmethod
    def save_policies_from(files_dir):
        if not Path(f'{files_dir}{FileOutput.POLICIES}').is_file():
            print('you have to generate policies first, please run\n')
            print(f'indentify.py {files_dir}')
            raise typer.Exit(1)
        presetname = typer.prompt("name for the preset:")
        if not Path(PathsConfig.PRESETS).is_dir():
            os.mkdir(PathsConfig.PRESETS)
        shutil.copy(f'{files_dir}{FileOutput.POLICIES}', Path(PathsConfig.PRESETS).joinpath(presetname))
        print(f'policies saved in {PathsConfig.PRESETS}/{presetname}')
        raise typer.Exit()
