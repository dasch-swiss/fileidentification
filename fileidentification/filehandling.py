import os
import shutil
import subprocess
import shlex
import re
import json
import logging
from dataclasses import dataclass, field
from abc import ABC
from typing import Union, Any, Dict, Type
from .wrappers.wrappers import ffmpeg_analyse_stream



SFinfo: Type = Dict[str, Any]
"""
single file information output of siegfried (json)

has the following values among others

{
    "filename": "abs/path/to/file.ext",
    "matches": [
        {
            "id": "puid",
            "warning": "some warnings"
        }
    ]
}
"""

@dataclass
class File:

    filepath: str = None
    puid: str = None
    filename: str = None  # without extension, this is different to the json output of siegfried, where its the abs path
    origin_dir: str = None
    target_dir: str = None
    cleanup: dict = field(default_factory=dict)

    def _mkdir(self):
        """create a folder with the name of the file"""
        self.target_dir = os.path.splitext(self.filepath)[0]
        self.origin_dir, self.filename = os.path.split(self.target_dir)
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
        # add cleanup instructions, move and remove
        self.cleanup['mv'] = [target, self.origin_dir]
        self.cleanup['rm'] = [self.filepath, self.target_dir]

    # file migration
    def convert(self, args: dict):
        """convert the file
        args: dict contains the name of the bin, the target container, and the additional arguments"""
        self._mkdir()

        # TODO Metadata such as exif... are lost when reencoded,
        #  need to implement something to copy some parts of these metadata?

        target = os.path.join(self.target_dir, f'{self.filename}.{args["target_container"]}')
        # set outputfile and log
        outfile = shlex.quote(target)
        logfile = shlex.quote(os.path.join(self.target_dir, f'{self.filename}.log'))
        match args["bin"]:
            # construct command if its ffmpeg
            case "ffmpeg":
                cmd = f'ffmpeg -y -i {shlex.quote(self.filepath)} {args["processing_args"]} {outfile} 2> {logfile}'
            # construct command if its imagemagick
            case "convert":
                cmd = f'convert {shlex.quote(self.filepath)} {args["processing_args"]} {outfile} 2> {logfile}'
            # construct command if its LibreOffice
            case "soffice":
                cmd = f'/Applications/LibreOffice.app/Contents/MacOS/soffice {args["processing_args"]} '
                cmd = cmd + f'{args["target_container"]} {shlex.quote(self.filepath)}'
                cmd = cmd + f' --outdir {shlex.quote(self.target_dir)} > {logfile}'
            case _:
                print(f'unknown bin {args["bin"]} in policies. aborting ...')
                quit()

        # run cmd in shell (and as a string, so [error]output is redirected to logfile)
        subprocess.run(cmd, shell=True)
        logging.info(f'did convert {self.filepath} to {outfile}')
        # add cleanup instructions, move and remove
        # only clean up when file conversion was successful
        if os.path.isfile(target):
            self.cleanup['mv'] = [target, self.origin_dir]
            self.cleanup['rm'] = [self.filepath, self.target_dir]



class FileHandler(ABC):

    policies: dict = None
    fmt2ext: dict = None
    cleanup: list = []

    def handle(self, sfinfos: list[SFinfo], cleanup=False) -> tuple[list, list]:
        """
        runs the files with the gathered siegfried information against the preservation policies
        :param sfinfos: file information output from siegfried (json)
        :param cleanup: bool if set to true, it replaces the original files with the converted ones, deletes created folders
        :return modified: original file information of the files that got converted or renamed
        """
        modified: list = []
        for sfinfo in sfinfos:
            sfinfo = self._check_against_policies(sfinfo)
            if sfinfo:
                modified.append(sfinfo)
        if cleanup:
            self._cleanup()
        return modified, self.cleanup

    def _check_against_policies(self, sfinfo: SFinfo) -> Union[SFinfo, None]:
        """
        :param sfinfo: json object with metadata of a single file generated with siegfried
        :return: the json object if any file manipulation occurred
        """

        sfinfo, puid = self._fetch_puid(sfinfo)
        if not puid:
            logging.error(f'could not handle {sfinfo['filename']}')
            return

        # os specific files we do not care, eg .DS_store etc #TODO there are more for sure
        if puid in ['fmt/394']:
            return

        # check if the file throws any errors while open/processing it with the respective exec
        self._check_fileintegrity(puid, sfinfo)

        # file conversion according to the policies defined in conf/policies.py
        # case where there is an extension missmatch, rename file
        if sfinfo['matches'][0]['warning'] == 'extension mismatch':
            file = File(filepath=sfinfo['filename'], puid=puid)
            ext = self.fmt2ext[puid]['file_extensions'][0]
            logging.info(f'extension missmatch detected, file {sfinfo["filename"]} should end with {ext}')
            # if it needs to be converted anyway
            if not self.policies[puid]['accepted']:
                file.convert(self.policies[puid])
                self.cleanup.append(file.cleanup)
                return sfinfo
            # if it needs just to be renamed
            file.rename(ext)
            self.cleanup.append(file.cleanup)
            return sfinfo

        # case where file needs to be converted
        if not self.policies[puid]['accepted']:
            file = File(filepath=sfinfo['filename'], puid=puid)
            file.convert(self.policies[puid])
            self.cleanup.append(file.cleanup)
            return sfinfo

        # case where file is accepted as it is, all good
        if self.policies[puid]['accepted']:
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
                return sfinfo, None
        else:
            puid = sfinfo['matches'][0]['id']

        return sfinfo, puid

    def _check_fileintegrity(self, puid: str, sfinfo: SFinfo) -> None:
        """"""
        # check stream integrity # TODO file integrity for other files than Audio/Video
        if self.policies[puid]["bin"] == "ffmpeg":
            ffmpeg_analyse_stream(sfinfo['filename'])


    def _cleanup(self):
        """cleans up the """
        for task in self.cleanup:
            for k in task.keys():
                match k:
                    case 'mv':
                        shutil.move(task[k][0], task[k][1])
                    case 'rm':
                        os.remove(task[k][0])
                        shutil.rmtree(task[k][1])

    def load_policies(self, policies_path: str, fmt2ext_path: str):
        if os.path.isfile(policies_path):
            with open(policies_path, 'r') as f:
                self.policies = json.load(f)
        if os.path.isfile(fmt2ext_path):
            with open(fmt2ext_path, 'r') as f:
                self.fmt2ext = json.load(f)

        self._assure_policies()

    def _assure_policies(self):
        if not self.policies:
            print('could not load policies. please check filepath')
            quit()
        for el in self.policies:
            if self.policies[el]['bin'] not in ['', 'ffmpeg', 'convert', 'soffice']:
                print(f'unknown bin {self.policies[el]["bin"]} found in policy {el}. aborting...')
                quit()