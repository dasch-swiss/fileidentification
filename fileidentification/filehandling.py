import os
import shutil
import subprocess
import shlex
import re
import json
import logging
from dataclasses import dataclass
from abc import ABC
from typing import Union, Any, Dict, Type
from .wrappers.wrappers import ffmpeg_analyse_stream
from .conf.policies import accepted, conversions


# fmt2ext dict for mapping extension mismatch
with open('fileidentification/conf/fmt2ext.json', 'r') as f:
    fmt2ext = json.load(f)


SFinfo: Type = Dict[str, Any]
# single file information output of siegfried (json)
# {
#     "filename": "abs/path/to/file.ext",
#     ...
#     "matches": [
#         {
#             "id": "fmt/id",
#             ...
#             "warning": "some warnings"
#         }
#     ]
# }


@dataclass
class File:
    filepath: str = None
    puid: str = None
    target_dir: str = None
    filename: str = None  # without extension, this is different to the json output of siegfried, where its the abs path
    migrated_filepath: str = None

    def _mkdir(self):
        """create a folder with the name of the file"""
        self.target_dir = os.path.splitext(self.filepath)[0]
        self.filename = os.path.split(self.target_dir)[-1]
        # case where there is no ext
        if not os.path.splitext(self.filepath)[1]:
            self.target_dir = f'{self.target_dir}Folder'
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)

    def rename(self, ext: str):
        """rename a copy of the file with the given ext"""
        self._mkdir()
        target = os.path.join(self.target_dir, f'{self.filename}.{ext}')
        shutil.copyfile(self.filepath, target)
        logging.info(f'did rename {self.filepath} to {target}')

    # file migration
    def convert(self, args: list):
        """convert the file
        args contains the name of the executable, the target container, and the arguments"""
        self._mkdir()

        # TODO Metadata such as exif... are lost when reencoded,
        #  need to implement something to copy some parts of these metadata?

        self.migrated_filepath = os.path.join(self.target_dir, f'{self.filename}.{args[1]}')
        # set outputfile and log
        outfile = shlex.quote(self.migrated_filepath)
        logfile = shlex.quote(os.path.join(self.target_dir, f'{self.filename}.log'))
        match args[0]:
            # construct command if its ffmpeg
            case "ffmpeg":
                cmd = f'ffmpeg -y -i {shlex.quote(self.filepath)} {args[2]} {outfile} 2> {logfile}'
            # construct command if its imagemagick
            case "convert":
                cmd = f'convert {shlex.quote(self.filepath)} {args[2]} {outfile} 2> {logfile}'
            # construct command if its LibreOffice
            case "soffice":
                cmd = f'/Applications/LibreOffice.app/Contents/MacOS/soffice {args[2]} {args[1]} {shlex.quote(self.filepath)}'
                cmd = cmd + f' --outdir {shlex.quote(self.target_dir)} 2> {logfile}'
            # no known exec selected
            case _:
                print(f'check conversion config for {self.puid}')
                return

        # run cmd in shell (and as a string, so [error]output is redirected to logfile)
        subprocess.run(cmd, shell=True)
        logging.info(f'did convert {self.filepath} to {outfile}')


class FileHandler(ABC):
    """
    Object to run a json formatted siegfried output against preservation policies
    """
    accepted: dict = accepted
    conversions: dict = conversions
    fmt2ext: dict = fmt2ext

    def run(self, sfinfos: list[SFinfo]) -> list:
        """
        :param sfinfos: a list of json formatted file information (siegfried output)
        :return modified: a list of json formatted file information for files that got converted, renamed
        """
        modified: list = []
        for sfinfo in sfinfos:
            sfinfo = self._check_against_policies(sfinfo)
            if sfinfo:
                modified.append(sfinfo)
        return modified

    def _check_against_policies(self, sfinfo: SFinfo) -> Union[SFinfo, None]:
        """
        :param sfinfo: json object with metadata of a single file generated with siegfried
        :return: the json object if any file manipulation occurred
        """

        sfinfo, puid = self._fetch_puid(sfinfo)
        if not puid:
            return

        # os specific files we do not care, eg .DS_store etc #TODO there are more for sure
        if puid in ['fmt/394']:
            return

        # check if the file throws any errors while open/processing it with the respective exec
        self._check_fileintegrity(puid, sfinfo)

        # file conversion according to the policies defined in conf/policies.py
        # case where there is a extension missmatch, rename file
        if sfinfo['matches'][0]['warning'] == 'extension mismatch':
            file = File(filepath=sfinfo['filename'], puid=sfinfo['matches'][0]['id'])
            ext = self.fmt2ext[puid]['file_extensions'][0]
            logging.info(f'extension missmatch detected, file {sfinfo["filename"]} should end with {ext}')
            # if it needs to be converted anyway
            if puid in conversions:
                file.convert(conversions[puid])
                return sfinfo
            # if it needs just to be renamed
            file.rename(ext)
            return sfinfo

        # case where file needs to be converted
        if puid in conversions:
            file = File(filepath=sfinfo['filename'], puid=sfinfo['matches'][0]['id'])
            file.convert(conversions[puid])
            return sfinfo

        # case where file is accepted as it is, all good
        if puid in accepted:
            return

        # case where puid is neither in accepted nor in migration_config
        logging.warning(f'{puid} is not know in policies... please check {sfinfo['filename']} and append it to policies')

    def _fetch_puid(self, sfinfo: SFinfo) -> tuple[SFinfo, Union[str, None]]:
        """parse the puid out of the json returned by siegfried"""
        if sfinfo['matches'][0]['id'] == 'UNKNOWN':
            # TODO fallback may need to be more elaborate, as it takes the first proposition of siegfried, i.e. fileext
            fmts = re.findall(r"(fmt|x-fmt)/([\d]+)", sfinfo['matches'][0]['warning'])
            fmts = [f'{el[0]}/{el[1]}' for el in fmts]
            if fmts:
                logging.warning(f'could not detect fmt on {sfinfo['filename']} \n falling back on ext and assuming its {fmts[0]}')
                puid = fmts[0]
            else:
                logging.error(f'could not handle {sfinfo['filename']}')
                return sfinfo, None
        else:
            puid = sfinfo['matches'][0]['id']

        return sfinfo, puid

    def _check_fileintegrity(self, puid: str, sfinfo: SFinfo) -> None:
        """"""
        # check stream integrity # TODO file integrity for other files than Audio/Video
        if puid in self.accepted and self.accepted[puid][0] == "ffmpeg":
            ffmpeg_analyse_stream(sfinfo['filename'])
        if puid in self.conversions and self.conversions[puid][0] == "ffmpeg":
            ffmpeg_analyse_stream(sfinfo['filename'])
