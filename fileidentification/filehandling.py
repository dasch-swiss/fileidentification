from __future__ import annotations
import sys
import os
import platform
import shutil
import json
import typer
from typing_extensions import Annotated
from time import time, sleep
from datetime import datetime
from typer import secho, colors
from enum import StrEnum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Union
from fileidentification.wrappers.wrappers import Siegfried as Sf, Ffmpeg, Converter as Con, ImageMagick, Rsync
from fileidentification.parser.parser import SFParser
from fileidentification.helpers import format_bite_size, get_hash
from conf.models import SfInfo, PathsConfig, CleanUpTable, LibreOfficePath, BasicAnalytics, LogTables, \
    FileDiagnosticsMsg, PolicyMsg, FileProcessingErr, LogMsg, FileOutput, ServerCon, SiegfriedConf, ProtocolErr
from conf.policies import PoliciesGenerator
from conf.policies import systemfiles


@dataclass
class Mode:
    """the different states for the filehandling classes. DRY: dry run,
    ADD: do not delete the original files of the files that got converted, VERBOSE: do verbose analysis of video files
    STRICT: move files that are not listed in policies to FAILED istead of skipping them / """
    DRY: bool = False
    ADD: bool = False
    VERBOSE: bool = False
    STRICT: bool = False
    QUIET: bool = False


@dataclass
class FileHandler:
    """
    It can create, verify and apply policies. convert files (with FileConverter) and cleanup (PostProcessor)
    """

    fmt2ext: dict = field(default_factory=dict)
    policies: dict = field(default_factory=dict)
    log_tables: LogTables = field(default_factory=LogTables)
    ba: BasicAnalytics = None
    pinned2protocol: list[SfInfo] = field(default_factory=list)
    pinned2convert: list[SfInfo] = field(default_factory=list)
    # processing states
    mode: Mode = field(default_factory=Mode)

    def __post_init__(self):
        with open(PathsConfig.FMT2EXT, 'r') as f:
            self.fmt2ext = json.load(f)

    def apply_policies(self, sfinfo: SfInfo) -> Union[SfInfo, None]:
        """
        apply the policies against the files. this is handled with the metadata SfInfo and the policies that can be
        loaded with the load_policies method. it also calls the check_fileintegrity method. when a file needs to be
        converted after a policies, it sets the Flag convert in SfInfo to True.
        returns None if the file passed all the tests. if not, it returns the updated metadata as SfInfo
        :param sfinfo the metadata
        """
        puid = sfinfo.processed_as
        if not puid:
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileProcessingErr.PUIDFAIL}'))
            self.move2failed(sfinfo)
            self.log_tables.append2processingerr(sfinfo, FileProcessingErr.PUIDFAIL)
            return

        if sfinfo.errors == FileDiagnosticsMsg.EMPTYSOURCE:
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileDiagnosticsMsg.EMPTYSOURCE}'))
            os.remove(sfinfo.filename)
            self.pinned2protocol.append(Postprocessor.set_relativepath(sfinfo))
            self.log_tables.append2diagnostics(sfinfo, FileDiagnosticsMsg.EMPTYSOURCE)
            return

        # os specific files we do not care, eg .DS_store etc
        if puid in systemfiles:  # ['fmt/394']:
            # could also simply remove them
            # os.remove(sfinfo.filename)
            return

        if puid not in self.policies:
            # in strict mode, move file
            if self.mode.STRICT:
                sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{PolicyMsg.NOTINPOLICIES}'))
                self.log_tables.append2policies(sfinfo, PolicyMsg.NOTINPOLICIES)
                self.move2failed(sfinfo)
                return
            # just flag it as skipped
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{PolicyMsg.SKIPPED}'))
            self.log_tables.append2policies(sfinfo, PolicyMsg.SKIPPED)
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
                # throw a warning if file is not going to be converted anyways
                if self.policies[puid]['accepted']:
                    secho(f'WARNING: you should manually rename {sfinfo.filename}\n{sfinfo.processing_logs}', fg=colors.YELLOW)

        # check if the file throws any errors while open/processing it with the respective bin
        # return it when its fatal
        if self._is_file_corrupt(sfinfo):
            sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileDiagnosticsMsg.CORRUPT}'))
            self.move2failed(sfinfo)
            return

        # case where file needs to be converted
        if not self.policies[puid]['accepted']:
            self.pinned2convert.append(sfinfo)
            return

        # case where file is accepted as it is, all good, append it to passed if flag in policies is true
        if self.policies[puid]['accepted']:
            if self.policies[sfinfo.processed_as]['force_protocol']:
                self.pinned2protocol.append(Postprocessor.set_relativepath(sfinfo))
            return

        # if you end up here, it is not a good sign
        secho(f'Error: {sfinfo.filename} escaped the policies assertion...', fg=colors.RED)
        sfinfo.processing_logs.append(LogMsg(name="filehandler", msg=f'{FileProcessingErr.ESCAPED}'))
        self.log_tables.append2processingerr(sfinfo, FileProcessingErr.ESCAPED)

    def move2failed(self, sfinfo: SfInfo):
        dest = Path(f'{sfinfo.files_dir}{PathsConfig.FAILED}' / sfinfo.relative_path)
        if not dest.exists():
            os.makedirs(dest)
        rstatus, msg, cmd = Rsync.copy(str(sfinfo.filename), str(dest), dry=self.mode.DRY)
        if not self.mode.DRY:
            sfinfo.processing_logs.append(LogMsg(name='rsync', msg=msg))
            self.pinned2protocol.append(Postprocessor.set_relativepath(sfinfo))
            self.ba.puid_unique[sfinfo.processed_as].remove(sfinfo)
            # if there was an error, append to processing err tables
            if rstatus:
                secho(f'{FileProcessingErr.FAILEDMOVE} {cmd}', fg=colors.RED)
                self.log_tables.append2processingerr(sfinfo, FileProcessingErr.FAILEDMOVE)
            return
        else:
            print(cmd)

    def _rename(self, sfinfo: SfInfo, ext: str):
        dest = sfinfo.filename.with_suffix(ext)
        # if a file with same name and extension already there, append file hash to name
        if Path(sfinfo.filename.with_suffix(ext)).is_file():
            dest = Path(sfinfo.files_dir / sfinfo.relative_path / f'{sfinfo.filename.stem}_{sfinfo.filehash}{ext}')
        msg = f'expecting {ext} : mv {sfinfo.filename} -> {dest}'
        if self.mode.DRY:
            print(msg)
        else:
            os.rename(sfinfo.filename, dest)
        sfinfo.filename = dest
        sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=msg))
        self.log_tables.append2diagnostics(sfinfo, FileDiagnosticsMsg.EXTMISMATCH)

    def load_policies(self, policies_path: Path):
        if policies_path.is_file():
            with open(policies_path, 'r') as f:
                self.policies = json.load(f)

        self._assert_policies()

    def _assert_policies(self):
        if not self.policies:
            print('could not load policies. please check filepath... exit')
            raise typer.Exit(1)
        for el in self.policies:
            if self.policies[el]['bin'] not in ['', 'ffmpeg', 'convert', 'soffice']:
                print(f'unknown bin {self.policies[el]["bin"]} found in policies {el}... exit')
                raise typer.Exit(1)

    def get_conversion_args(self, sfinfo: SfInfo) -> dict:
        return self.policies[sfinfo.processed_as]

    @staticmethod
    def append_path_values(sfinfo: SfInfo, files_dir: Path, wdir: Path) -> SfInfo:
        sfinfo.relative_path = sfinfo.filename.parent.relative_to(files_dir)
        sfinfo.files_dir = files_dir
        sfinfo.wdir = wdir
        return sfinfo

    def gen_default_policies(self, files_dir: Path, sfinfos: list[SfInfo],
                             blank: bool = False, extend: str = None) -> None:
        """
        generates a policies.json with the default values stored in conf.policies.py with the encountered fileformats (they
        are passed with a list of SfInfos. this is done by loading the sfinfo values into an BasicAnalytics table. that
        table can generate policies among printing out some basic analytics.
        returns the path of the policies.json
        :param files_dir the directory with the files to generate a default policies file
        :param sfinfos the SfInfo objecs
        :param blank if set to True, it generates a blank policies.json
        :param extend if true, it expands the loaded policies with filetypes found in files_dir that are not in the
        loaded policies and writes out an updated policies.json
        """
        self.run_basic_analytics(sfinfos=sfinfos)

        if extend:
            name = extend
            self.ba.presets = {}
            extend = self.policies
            [self.ba.presets.update({k: name}) for k in self.policies]

        pol_gen = PoliciesGenerator(fmt2ext=self.fmt2ext)
        self.policies, self.ba = pol_gen.gen_policies(files_dir, ba=self.ba, strict=self.mode.STRICT,
                                                      keep=self.mode.ADD, blank=blank, extend=extend)
        if not self.mode.QUIET:
            RenderTables.print_fileformats(self, puids=[el for el in self.ba.puid_unique])
            print(f'\nyou find the policies in {files_dir}_policies.json, if you want to modify them')
            if self.ba.blank:
                print(f'there are some non default policies: {[el for el in self.ba.blank]}\n',
                      f'-> you may adjust them (they are set as accepted now)')

    def run_basic_analytics(self, sfinfos: list[SfInfo]) -> None:

        self.ba = BasicAnalytics(fmt2ext=self.fmt2ext)
        [self.ba.append(sfinfo) for sfinfo in sfinfos]

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
            case "ffmpeg":
                if self.mode.DRY:
                    _, cmd, specs = Ffmpeg.is_corrupt(sfinfo, dry=True, verbose=self.mode.VERBOSE)
                    print([cmd])
                    return _
                corrupt, error, specs = Ffmpeg.is_corrupt(sfinfo, verbose=self.mode.VERBOSE)
                if specs:
                    sfinfo.codec_info.append(LogMsg(name='ffmpeg', msg=specs))
                if error:
                    sfinfo.processing_logs.append(LogMsg(name='ffmpeg', msg=error))
            case "convert":
                if self.mode.DRY:
                    _, cmd, specs = ImageMagick.is_corrupt(sfinfo, dry=True)
                    print([cmd])
                    return _
                corrupt, error, specs = ImageMagick.is_corrupt(sfinfo)
                if specs:
                    sfinfo.codec_info.append(LogMsg(name='imagemagick', msg=specs))
                if error:
                    sfinfo.processing_logs.append(LogMsg(name='imagemagick', msg=error))
            case _:
                return False

        if corrupt:
            self.log_tables.append2diagnostics(sfinfo, FileDiagnosticsMsg.CORRUPT)
            return True
        if error:
            self.log_tables.append2diagnostics(sfinfo, FileDiagnosticsMsg.MINORERROR)
            return False
        return False

    def test_policies(self, sfinfos: list[SfInfo], files_dir: Path, puid: str = None) -> None:
        """test a policies.json with the smallest files of the directory. if puid is passed, it only tests the puid
        of the policies."""
        puids: list = []
        if not self.ba:
            self.run_basic_analytics(sfinfos)
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

            test_conv = FileConverter(mode=self.mode, policies=self.policies)

            for puid in puids:
                sample = self.ba.puid_unique[puid][0]
                if not self.mode.QUIET:
                    if isinstance(self.policies[puid]["expected"], list):
                        print(f'\n--> for [{puid}] {self.fmt2ext[puid]["name"]} {self.fmt2ext[puid]["file_extensions"]}\n'
                              f'expecting {self.policies[puid]["expected"]}'
                              f'{self.fmt2ext[self.policies[puid]["expected"][0]]["name"]} '
                              f'{self.fmt2ext[self.policies[puid]["expected"][0]]["file_extensions"]}')

                    print(f'\ntesting it with:\n'
                          f'{Con.convert(sample, self.get_conversion_args(sample), dry=True)[1]}')
                test, duration = test_conv.run_test(sample)
                if not test.processing_error:
                    if not self.mode.QUIET:
                        est_time = self.ba.total_size[puid] / test.derived_from.filesize * duration
                        print(f'\napplying the policies for this filetype would appoximatly take '
                              f'{int(est_time) / 60: .2f} min. You find the file with the log in {test.filename.parent}')

    def convert(self, sfinfos: list[SfInfo]) -> list[SfInfo]:
        """convert files whose metadata are in a list of SfInfos"""
        fc = FileConverter(mode=self.mode, policies=self.policies)

        stack: list[SfInfo] = []

        for sfinfo in sfinfos:
            sfinfo, _ = fc.convert(sfinfo)
            if not sfinfo.processing_error:
                stack.append(sfinfo)
            else:
                self.log_tables.append2processingerr(sfinfo, sfinfo.processing_error)

        return stack


class FileConverter:

    def __init__(self, mode, policies):
        self.mode: Mode = mode
        self.policies: dict = policies

    def analyse_append_log(self, sfinfo: SfInfo, target: Path, processing_log: LogMsg | None, expected: list) \
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
            pcs_sfinfo = SFParser.to_SfInfo(Sf.analyse(target)[0])
            if processing_log:
                pcs_sfinfo.processing_logs.append(processing_log)
            # only add postprocessing information if conversion was successful
            if pcs_sfinfo.processed_as not in expected:
                p_error = f' did expect {expected}, got {pcs_sfinfo.processed_as} instead'
                pcs_sfinfo.processing_error = FileProcessingErr.NOTEXPECTEDFMT
                pcs_sfinfo.processing_logs.append(
                    LogMsg(name='filehandler', msg=f'{FileProcessingErr.NOTEXPECTEDFMT}' + p_error))
                secho(f'\nERROR: {p_error} when converting {sfinfo.filename} to {target}', fg=colors.YELLOW, bold=True)
            else:
                cu_table = CleanUpTable(
                    filename=target,
                    dest=Path(sfinfo.filename.parent),
                    # only add the path to the original file if the policy says so
                    delete_original=sfinfo.filename if not self.policies[sfinfo.processed_as]['keep_original'] else None,
                    wdir=target.parent,
                    filehash=pcs_sfinfo.filehash,
                    relative_path=sfinfo.relative_path
                )
                pcs_sfinfo.cu_table = cu_table
                if not self.mode.QUIET:
                    secho(f'\n[{sfinfo.filename} -> {target}]', fg=colors.GREEN, bold=True)
            # set relative path in original file metadata, append it as derived_from to the converted one
            Postprocessor.set_relativepath(sfinfo)
            pcs_sfinfo.derived_from = sfinfo

        else:
            # conversion error, nothing to analyse
            pcs_sfinfo = sfinfo
            pcs_sfinfo.processing_error = FileProcessingErr.CONVFAILED
            pcs_sfinfo.processing_logs.append(LogMsg(name='filehandler', msg=f'{FileProcessingErr.CONVFAILED}'))
            secho(f'\nERROR failed to convert {sfinfo.filename} to {target}', fg=colors.RED, bold=True)

        return pcs_sfinfo

    # file migration
    def convert(self, sfinfo: SfInfo) -> tuple[SfInfo, list]:
        """
        convert a file, returns the metadata of the converted file as SfInfo
        :param sfinfo the metadata of the file to convert, updated if successfully converted
        """
        # match platform
        if platform.system() == LibreOfficePath.Darwin.name:
            soffice = Path(LibreOfficePath.Darwin)
        elif platform.system() == LibreOfficePath.Linux.name:
            soffice = Path(LibreOfficePath.Linux)
        else:
            soffice = None
            print('convert not possible with your OS. sorry')
            self.mode.DRY = True

        args = self.policies[sfinfo.processed_as]

        target_path, cmd, logfile_path = Con.convert(sfinfo, args, soffice, self.mode.DRY)

        if self.mode.DRY:
            print([cmd])
        else:
            # replace abs path in logs, add name
            processing_log = None
            logtext = logfile_path.read_text().replace(f'{sfinfo.files_dir}/', "").replace(f'{sfinfo.wdir}/', "")
            if logtext != "":
                processing_log = LogMsg(name=f'{args["bin"]}', msg=logtext)

            # create an SfInfo for target - and if conversion succesfull append the original as parent to it
            # else return original with sfinfo.processing_error
            sfinfo = self.analyse_append_log(sfinfo, target_path, processing_log, args['expected'])

        return sfinfo, [cmd]

    def run_test(self, sfinfo: SfInfo) -> tuple[SfInfo, float]:
        sfinfo.wdir = Path(sfinfo.wdir / PathsConfig.TEST)
        start = time()
        test, _, = self.convert(sfinfo)
        duration = time() - start
        return test, duration


class Postprocessor:
    """
    during file conversion, it receives the cleanup instructions as a CleanUpTable per file conversion
    it can turn the absolute paths of the SfInfo into relative paths,
    delete working directories, move the converted files and delete the ones that are replaced
    """
    def __init__(self, mode):
        self.mode: Mode = mode

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

    def cleanup(self, sfinfos: list[SfInfo], processed: list[SfInfo], files_dir: Path,
                wdir: Path = None, server: ServerCon = None) \
            -> list[SfInfo]:
        stack: [SfInfo] = []
        failed: [SfInfo] = []
        for sfinfo in sfinfos:
            if sfinfo.cu_table:
                tb = sfinfo.cu_table
                # delete the original if its mentioned, gets overwritten if mode.ADD
                # remove it from already processed (e.g. if chain conversion)
                if tb.delete_original and tb.delete_original.is_file():
                    if not self.mode.ADD:
                        os.remove(tb.delete_original)
                        if processed:
                            [processed.remove(el) for el in processed if
                             sfinfo.derived_from.filename == el.filename]
                # append hash to filename if the path already exists
                if Path(tb.dest / tb.filename.name).is_file():
                    tb.dest = tb.dest / f'{tb.filename.stem}_{tb.filehash}{tb.filename.suffix}'
                source, dest = str(tb.filename), str(tb.dest)
                # make an additional folder with hash if server, to be sure not to overwrite something
                if server:
                    dest = f'{tb.relative_path}/{tb.filename.stem}_{tb.filehash}/'
                # move the file
                rstatus, msg, cmd = Rsync.copy(source, dest, dry=self.mode.DRY, server=server)
                if not self.mode.DRY:
                    # check if the return status is true
                    if not rstatus:
                        # set relative path in sfinfo, remove cu_tables
                        sfinfo = self.set_relativepath(sfinfo, tb.dest)
                        sfinfo.cu_table = None
                        # only remove working dir if rsync is successful
                        if tb.wdir.is_dir() and not server:
                            shutil.rmtree(tb.wdir)
                        sfinfo.processing_logs.append(LogMsg(name='rsync', msg=msg))
                        stack.append(sfinfo)
                    else:  # rsync failed
                        secho(cmd, fg=colors.RED, bold=True)
                        sfinfo.processing_logs.append(LogMsg(name='rsync', msg=msg))
                        failed.append(sfinfo)
                # dry version of it
                else:
                    print(cmd)
                    if not self.mode.ADD:
                        if tb.delete_original:
                            print(f'RM {tb.delete_original}')
                    print(f'RM {tb.wdir}')
        stack.extend(processed)
        if failed:
            self.dump_json(failed, files_dir, FileOutput.FAILED)
        # remove tmp protocol empty folders if exists, if not evoked with server params (i.e. sending it to remote)
        if not server:
            self._remove_tmp(wdir, files_dir)

        return stack

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
    def verify_file(file: Path, sha256: bool = False) -> Path | str:
        """verifies file with hash"""
        if not file.is_file():
            return ProtocolErr.NOFILE
        else:
            if not sha256:
                return file
            if sha256 and Path(f'{file}.sha256').is_file():
                sha256 = Path(f'{file}.sha256').read_text()
                if not sha256 == get_hash(file):
                    return ProtocolErr.MODIFIED
                return file
            return ProtocolErr.NOHASH

    def _remove_tmp(self, wdir: Path, files_dir: Path):
        for path, _, _ in os.walk(wdir, topdown=False):
            if len(os.listdir(path)) == 0:
                os.rmdir(path)
        if Path(f'{files_dir}{FileOutput.TMPSTATE}').is_file():
            os.remove(f'{files_dir}{FileOutput.TMPSTATE}')
            os.remove(f'{files_dir}{FileOutput.TMPSTATE}.sha256')
        if wdir.joinpath(PathsConfig.TEST).is_dir():
            shutil.rmtree(wdir.joinpath(PathsConfig.TEST))


class PreProcessor:

    def __init__(self, mode, policies):
        self.mode: Mode = mode
        self.policies = policies

    def fetch_remote(self, sfinfos: list[SfInfo], server: ServerCon, files_dir) -> None:

        failed: list[SfInfo] = []
        for sfinfo in sfinfos:
            if sfinfo.processed_as not in self.policies or not self.policies[sfinfo.processed_as]['accepted'] or self.mode.ADD:
                err, msg, cmd = Rsync.fetch(str(sfinfo.filename), str(files_dir / sfinfo.filename.parent),
                                            server, dry=self.mode.DRY)
                if not self.mode.DRY:
                    if err:
                        print(f'could not fetch {sfinfo.filename}: {msg}')
                        failed.append(sfinfo)
                    else:
                        sfinfo.processing_logs.append(LogMsg(name='rsync', msg=msg))
                else:
                    print(cmd)
        if failed:
            Postprocessor.dump_json(failed, files_dir, FileOutput.FAILED)


class RenderTables:
    def __init__(self, mode):
        self.mode: Mode = mode

    @staticmethod
    def print_siegfried_errors(fh: FileHandler):
        if fh.ba.siegfried_errors:
            print('got the following errors from siegfried')
            for sfinfo in fh.ba.siegfried_errors:
                print(f'{sfinfo.filename} \n{sfinfo.errors} {sfinfo.processing_logs}')
    @staticmethod
    def print_duplicates(fh):
        """prints out the used hash algorithm, the hash and the files that have the same hash"""
        # pop uniques files
        [fh.ba.filehashes.pop(k) for k in fh.ba.filehashes.copy() if len(fh.ba.filehashes[k]) == 1]
        if fh.ba.filehashes:
            print("\n----------- duplicates -----------")
            for k in fh.ba.filehashes:
                print(f'\n{SiegfriedConf.ALG}: {k} - files: ')
                [print(f'{path}') for path in fh.ba.filehashes[k]]

    @staticmethod
    def print_fileformats(fh: FileHandler, puids: list[str], verbose: bool = False):
        print("\n----------- fileformats -----------")
        for puid in puids:
            bytes_size: int = 0
            for sfinfo in fh.ba.puid_unique[puid]:
                bytes_size += sfinfo.filesize
            fh.ba.total_size[puid] = bytes_size
            size = format_bite_size(bytes_size)
            nbr, fmtname, = f'{len(fh.ba.puid_unique[puid]): >5}', f'{fh.fmt2ext[puid]["name"]}'
            if fh.mode.STRICT and puid not in fh.policies:
                pn = "strict"
                secho(f'{nbr}    {size: >10}    {puid: <10}    {pn: <10}    {"": <9}    {fmtname}', fg=colors.RED)
            if puid in fh.policies and not fh.policies[puid]['accepted']:
                bin = fh.policies[puid]['bin']
                pn = ""
                if fh.ba.presets and puid in fh.ba.presets:
                   pn = fh.ba.presets[puid]
                secho(f'{nbr}    {size: >10}    {puid: <10}    {pn: <10}    {bin: <10}   {fmtname}', fg=colors.YELLOW)
            if puid in fh.policies and fh.policies[puid]['accepted']:
                pn = ""
                if fh.ba.blank and puid in fh.ba.blank:
                    pn = "blank"
                if fh.ba.presets and puid in fh.ba.presets:
                   pn = fh.ba.presets[puid]
                print(f'{nbr}    {size: >10}    {puid: <10}    {pn: <10}    {"": <9}    {fmtname}')

            # we want the smallest file first for running the test in FileHandler.test_conversion()
            fh.ba.puid_unique[puid] = fh.ba.sort_by_filesize(fh.ba.puid_unique[puid])
            if verbose:
                print("\n")
                [print(f'{format_bite_size(sfinfo.filesize): >19} {sfinfo.filename}')
                 for sfinfo in fh.ba.puid_unique[puid]]
                print("\n")

    def print_diagnostic_table(self, fh: FileHandler) -> None:
        """lists all corrupt files with the respective errors thrown"""
        if fh.log_tables.diagnostics:
            if FileDiagnosticsMsg.CORRUPT.name in fh.log_tables.diagnostics.keys():
                print("\n----------- corrupt -----------")
                for sfinfo in fh.log_tables.diagnostics[FileDiagnosticsMsg.CORRUPT.name]:
                    print(f'\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}')
                    print(sfinfo.processing_logs)
            if self.mode.VERBOSE:
                if FileDiagnosticsMsg.MINORERROR.name in fh.log_tables.diagnostics.keys():
                    print("\n----------- minor errors -----------")
                    for sfinfo in fh.log_tables.diagnostics[FileDiagnosticsMsg.MINORERROR.name]:
                        print(f'\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}')
                        print(sfinfo.processing_logs)
                if FileDiagnosticsMsg.EXTMISMATCH.name in fh.log_tables.diagnostics.keys():
                    print("\n----------- extension missmatch -----------")
                    for sfinfo in fh.log_tables.diagnostics[FileDiagnosticsMsg.EXTMISMATCH.name]:
                        print(f'\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}')
                        print(sfinfo.processing_logs)
                print("\n")

    def print_policies_errors(self, fh: FileHandler) -> None:

        if fh.log_tables.policies[PolicyMsg.NOTINPOLICIES]:
            print(f'--> running in strict mode: moved the following files to {PathsConfig.FAILED}')
            [print(f'{el.processed_as: <10}{el.filename}') for el in fh.log_tables.policies[PolicyMsg.NOTINPOLICIES]]
        if self.mode.VERBOSE:
            if fh.log_tables.policies[PolicyMsg.SKIPPED]:
                print(f'--> skipped these files, their fmt is not in policies:')
                [print(f'{el.processed_as: <10}{el.filename}') for el in fh.log_tables.policies[PolicyMsg.NOTINPOLICIES]]

    @staticmethod
    def print_conv_tables(fh: FileHandler) -> None:
        if fh.pinned2convert:
            print("\n -------- file conversion settings -------")
            for puid in fh.ba.puid_unique:
                if not fh.policies[puid]['accepted'] and isinstance(fh.policies[puid]["expected"], list):
                    print(f'\n--> for [{puid}] {fh.fmt2ext[puid]["name"]} {fh.fmt2ext[puid]["file_extensions"]}\n'
                          f'expecting {fh.policies[puid]["expected"]} '
                          f'{fh.fmt2ext[fh.policies[puid]["expected"][0]]["name"]} '
                          f'{fh.fmt2ext[fh.policies[puid]["expected"][0]]["file_extensions"]}')

    @staticmethod
    def print_processing_table(fh: FileHandler) -> None:
        # TODO
        pass

    def report2file(self, fh: FileHandler, path: Path) -> None:
        default = sys.stdout
        with open(f'{path}_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt', 'a') as f:
            sys.stdout = f
            self.print_siegfried_errors(fh)
            self.print_fileformats(fh, puids=[el for el in fh.ba.puid_unique], verbose=self.mode.VERBOSE)
            self.print_duplicates(fh)
            self.print_diagnostic_table(fh)
            self.print_conv_tables(fh)
            sys.stdout = default

        print(f'report written to {path}_report.txt')


def save_policies_from(files_dir: Annotated[Path, typer.Argument(help="path to the directory or file")]):
    if not Path(f'{files_dir}{FileOutput.POLICIES}').is_file():
        print('you have to generate policies first, please run\n')
        print(f'indentify.py {files_dir}')
        raise typer.Exit(1)
    presetname = typer.prompt("name for the preset")
    if not Path(PathsConfig.PRESETS).is_dir():
        os.mkdir(PathsConfig.PRESETS)
    shutil.copy(f'{files_dir}{FileOutput.POLICIES}', Path(PathsConfig.PRESETS).joinpath(presetname))
    print(f'policies saved in {PathsConfig.PRESETS}/{presetname}')
    raise typer.Exit()


def clean_up(files_dir: Annotated[Path, typer.Argument(help="path to the directory or file")],
             wdir: Annotated[Path, typer.Option("--working-dir", "-w",
                    help="path to working dir where the processed files are stored")] = None,
             mode_add: Annotated[bool, typer.Option("--keep", "-k",
                    help="only adds the converted file, does not delete the original one")] = False,
             mode_dry: Annotated[bool, typer.Option("--dry", "-d",
                    help="dry run, not moving or converting files, just printing cmds")] = False,
             mode_set: Mode = None,
             ):

    mode = Mode(DRY=mode_dry, ADD=mode_add) if not mode_set else mode_set
    processed = parse_protocol(files_dir)
    pp = Postprocessor(mode=mode)
    tmp_protocol = pp.verify_file(Path(f'{files_dir}{FileOutput.TMPSTATE}'), sha256=True)
    if isinstance(tmp_protocol, Path):
        stack = SFParser.read_protocol(tmp_protocol)
        stack = pp.cleanup(stack, processed, files_dir, wdir)
        pp.dump_json(stack, files_dir, FileOutput.PROTOCOL, sha256=True)
        print('..did clean up. exiting...')
        raise typer.Exit()
    else:
        if tmp_protocol == ProtocolErr.NOHASH:
            secho(f'ERROR: this is bad, {ProtocolErr.NOHASH}, not moving or removing files', fg=colors.RED, bold=True)
            raise typer.Exit(1)
        if tmp_protocol == ProtocolErr.MODIFIED:
            secho(f'ERROR: this is bad, {ProtocolErr.MODIFIED}, not moving or removing files', fg=colors.RED, bold=True)
            raise typer.Exit(1)


def parse_protocol(files_dir) -> list[SfInfo]:

    protocol = Postprocessor.verify_file(Path(f'{files_dir}{FileOutput.PROTOCOL}'), sha256=True)
    processed: list[SfInfo] = []
    if isinstance(protocol, Path):
        processed.extend(SFParser.read_protocol(protocol))
    else:
        if protocol != ProtocolErr.NOFILE:
            secho(f'WARNING: {protocol}, i might stumble parsing it', fg=colors.YELLOW)
            sleep(0.5)
            processed.extend(SFParser.read_protocol(Path(f'{files_dir}{FileOutput.PROTOCOL}')))
    return processed
