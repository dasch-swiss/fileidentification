import logging
import os
import shutil
import subprocess
import shlex
import re
from dataclasses import dataclass
from typing import Union, Any, Dict
from .wrappers.wrappers import ffmpeg_analyse_stream


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
        # case where there is no ext
        if not os.path.splitext(self.filepath)[1]:
            self.target_dir = f'{self.target_dir}Folder'
        self.filename = os.path.split(self.target_dir)[-1]
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)

    def rename(self, ext: str):
        """rename a copy of the file with the given ext"""
        self._mkdir()
        target = os.path.join(self.target_dir, f'{self.filename}.{ext}')
        shutil.copyfile(self.filepath, target)
        logging.info(f'extension missmatch: did rename {self.filepath} to {target}')

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


def check_against_policies(obj: Dict[str, Any], fmt2ext: dict, accepted: list, conversions: dict) \
                           -> Union[dict[str, Any], None]:

    """
    run the siegfried output against the policies
    :param obj: json object with metadata of a single file generated with siegfried
    :param fmt2ext: dict that maps fmt to a file extension
    :param accepted: list of puid of files we accept as they are
    :param conversions: a dict containing instructions to convert a specific file
    :return: the json object if any file manipulation occurred
    """

    obj, puid = fetch_puid(obj)
    if not puid:
        return

    # os specific files we do not care, eg .DS_store etc #TODO there are more for sure
    if puid in ['fmt/394']:
        return

    # check if the file throws any errors while open/processing it with the respective exec
    check_fileintegrity(puid, obj)

    # file conversion according to the policies defined in conf/policies.py
    # case where there is a extension missmatch, rename file
    if obj['matches'][0]['warning'] == 'extension mismatch':
        file = File(filepath=obj['filename'], puid=obj['matches'][0]['id'])
        # if it needs to be converted anyway
        if puid in conversions:
            file.convert(conversions[puid])
            return obj
        # if it needs just to be renamed
        ext = fmt2ext[puid]['file_extensions'][0]
        file.rename(ext)
        return obj

    # case where file needs to be converted
    if puid in conversions:
        file = File(filepath=obj['filename'], puid=obj['matches'][0]['id'])
        file.convert(conversions[puid])
        return obj

    # case where file is accepted as it is, all good
    if puid in accepted:
        return

    # case where puid is neither in accepted nor in migration_config
    logging.warning(f'{puid} is not know in policies... please check {obj['filename']} and append it to policies')


def fetch_puid(obj: dict[str, Any]) -> tuple[dict[str, Any], Union[str, None]]:
    """parse the puid out of the json returned by siegfried"""
    if obj['matches'][0]['id'] == 'UNKNOWN':
        # TODO fallback may need to be more elaborate, as it takes the first proposition of siegfried, i.e. fileext
        fmts = re.findall("fmt/[0-9]$", obj['matches'][0]['warning'])
        if fmts:
            logging.warning(f'could not detect fmt on {obj['filename']} \n falling back on ext and assuming its {fmts[0]}')
            puid = fmts[0]
        else:
            logging.error(f'could not handle {obj['filename']}')
            return obj, None
    else:
        puid = obj['matches'][0]['id']

    return obj, puid


def check_fileintegrity(puid: str, obj: dict[str, Any]) -> None:

    # check stream integrity # TODO file integrity for other files than Audio/Video
    if puid in ['fmt/569', 'fmt/5', 'fmt/199']:
        ffmpeg_analyse_stream(obj['filename'])
