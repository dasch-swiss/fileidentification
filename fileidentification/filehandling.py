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
from .wrappers.wrappers import ffmpeg_analyse_stream, sf_analyse


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
    target: str = None
    origin_dir: str = None
    target_dir: str = None
    cleanup: dict = field(default_factory=dict)

    def _mkdir(self):
        """create a folder with the name of the file, set origin_dir, filename"""
        self.target_dir = os.path.splitext(self.filepath)[0]
        self.origin_dir, self.filename = os.path.split(self.target_dir)
        # case where there is no ext
        if not os.path.splitext(self.filepath)[1]:
            self.target_dir = f'{self.target_dir}Folder'
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)

    def _analyse_append_log(self, processing_log: str = None) -> SFinfo:
        "analyse the created file with siegfried, "
        if os.path.isfile(self.target):
            sfinfo = sf_analyse(self.target)[0]
        else:
            # conversion error, nothing to analyse
            sfinfo: dict = {}
            sfinfo['error'] = f'conversion failed. see processing_log for more information'
        processing_info = f'did process {self.filepath} to {self.target}'
        logging.info(processing_info)
        sfinfo['processing_info'] = processing_info
        if processing_log:
            sfinfo['processing_log'] = processing_log
        return sfinfo

    def rename(self, ext: str) -> SFinfo:
        """rename a copy of the file with the given ext"""
        self._mkdir()
        self.target = os.path.join(self.target_dir, f'{self.filename}.{ext}')
        shutil.copyfile(self.filepath, self.target)
        # add cleanup instructions, move and remove
        self.cleanup['mv'] = [self.target, self.origin_dir]
        self.cleanup['rm'] = [self.filepath, self.target_dir]
        # log and return sfinfo of target
        sfinfo = self._analyse_append_log()
        return sfinfo

    # file migration
    def convert(self, args: dict) -> SFinfo:
        """convert the file
        args: dict contains the name of the bin, the target container, and the additional arguments"""
        self._mkdir()

        # TODO Metadata such as exif... are lost when reencoded,
        #  need to implement something to copy some parts of these metadata?

        self.target = os.path.join(self.target_dir, f'{self.filename}.{args["target_container"]}')
        # set outputfile and log
        outfile = shlex.quote(self.target)
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
        # add cleanup instructions, move and remove
        # only clean up when file conversion was successful
        if os.path.isfile(self.target):
            self.cleanup['mv'] = [self.target, self.origin_dir]
            self.cleanup['rm'] = [self.filepath, self.target_dir]
        # log and return sfinfo of target
        with open(os.path.join(self.target_dir, f'{self.filename}.log'), 'r') as f:
            processing_log = f.read()
        sfinfo = self._analyse_append_log(processing_log)
        return sfinfo


class FileHandler(ABC):

    policies: dict = None
    fmt2ext: dict = None
    cleanup_instruction: list[dict] = []

    def handle(self, sfinfos: list[SFinfo], cleanup=False) -> Union[tuple[list, list], list]:
        """
        runs siegfried information of the files against the preservation policies
        :param sfinfos: file information output from siegfried (json)
        :param cleanup: bool if set to true, it replaces the original files with the converted ones, deletes created folders
        :returns modified: siegfried output of the processed file, with the processing logs and siegfried info of original file
        :returns cleanup_instruction: a list with cleanup instructions if not cleanup is set to False (default)
        """
        modified: list = []
        for sfinfo in sfinfos:
            sfinfo = self._check_against_policies(sfinfo)
            if sfinfo:
                modified.append(sfinfo)
        if cleanup:
            self._cleanup()
            return modified

        return modified, self.cleanup_instruction

    def _check_against_policies(self, sfinfo: SFinfo) -> Union[SFinfo, None]:
        """
        :param sfinfo: dict with metadata of a single file generated with siegfried
        :return: the dict if any file manipulation occurred
        """

        puid = self._fetch_puid(sfinfo)
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
                processed_sfinfo = file.convert(self.policies[puid])
                processed_sfinfo['original_file'] = sfinfo
                self.cleanup_instruction.append(file.cleanup)
                return processed_sfinfo
            # if it needs just to be renamed
            processed_sfinfo = file.rename(ext)
            processed_sfinfo['original_file'] = sfinfo
            self.cleanup_instruction.append(file.cleanup)
            return processed_sfinfo

        # case where file needs to be converted
        if not self.policies[puid]['accepted']:
            file = File(filepath=sfinfo['filename'], puid=puid)
            processed_sfinfo = file.convert(self.policies[puid])
            processed_sfinfo['original_file'] = sfinfo
            self.cleanup_instruction.append(file.cleanup)
            return processed_sfinfo

        # case where file is accepted as it is, all good
        if self.policies[puid]['accepted']:
            return

        # case where puid is neither in accepted nor in migration_config
        logging.warning(f'{puid} is not know in policies... please check {sfinfo['filename']} and append it to policies')

    def _fetch_puid(self, sfinfo: SFinfo) -> Union[str, None]:
        """parse the puid out of the json returned by siegfried"""
        if sfinfo['matches'][0]['id'] == 'UNKNOWN':
            # TODO fallback may need to be more elaborate, as it takes the first proposition of siegfried, i.e. fileext
            fmts = re.findall(r"(fmt|x-fmt)/([\d]+)", sfinfo['matches'][0]['warning'])
            fmts = [f'{el[0]}/{el[1]}' for el in fmts]
            if fmts:
                logging.warning(f'could not detect fmt on {sfinfo['filename']} \n falling back on ext and assuming its {fmts[0]}')
                puid = fmts[0]
            else:
                return
        else:
            puid = sfinfo['matches'][0]['id']

        return puid

    def _check_fileintegrity(self, puid: str, sfinfo: SFinfo) -> None:
        """"""
        # check stream integrity # TODO file integrity for other files than Audio/Video
        if self.policies[puid]["bin"] == "ffmpeg":
            ffmpeg_analyse_stream(sfinfo['filename'])

    def _cleanup(self):
        """cleans up the """
        for task in self.cleanup_instruction:
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