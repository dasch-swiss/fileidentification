from __future__ import annotations
import datetime
from typing import Type, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from fileidentification.conf.settings import SiegfriedConf
from enum import StrEnum
from pathlib import Path


@dataclass
class LogMsg:
    name: str = None
    msg: str = None
    timestamp: str = field(default_factory=str)

    def __post_init__(self):
        self.timestamp = str(datetime.datetime.now(datetime.UTC))


@dataclass
class SfInfo:
    """file info object mapped from siegfried output, gets extended while processing."""
    # output from siegfried
    filename: Path
    filesize: int = ""
    modified: str = ""
    errors: str = ""
    filehash: str = ""
    matches: Optional[list[Match]] = field(default_factory=list)
    # added during processing
    status: Status = None
    processed_as: Optional[str] = None
    media_info: Optional[list[LogMsg]] = field(default_factory=list)
    processing_logs: Optional[list[LogMsg]] = field(default_factory=list)
    # if converted
    derived_from: Optional[SfInfo] = None
    dest: Optional[Path] = None
    # paths used during processing, they are not written out to status.json
    path: Optional[Path] = None
    root_folder: Optional[Path] = None
    wdir: Optional[Path] = None

    def __post_init__(self):
        self.status = Status()

    def as_dict(self):
        """return the class as dict, with Path as string, None values skipped, recursive for derived_from"""
        # the output from siegfried
        res = {"filename": f'{self.filename}',
               "filesize": self.filesize,
               "modified": self.modified,
               "errors": self.errors,
               SiegfriedConf.ALG: self.filehash}

        if self.matches:
            res['matches'] = [{key.replace("formatname", "format").replace("formatclass", "class"): value
                               for key, value in asdict(match).items()}
                              for match in self.matches]

        # values added during processing

        res['status'] = asdict(self.status)

        if self.processed_as:
            res['processed_as'] = self.processed_as
        if self.media_info:
            res['media_info'] = [{k: v for k, v in asdict(el).items()} for el in self.media_info]
        if self.processing_logs:
            res['processing_logs'] = [{k: v for k, v in asdict(el).items()} for el in self.processing_logs]
        if self.dest:
            res['dest'] = f'{self.dest}'
        if self.derived_from:
            res['derived_from'] = self.derived_from.as_dict()

        return res

    def set_processing_paths(self, root_folder: Path, wdir: Path, initial=False):

        if root_folder.is_file():
            root_folder = root_folder.parent
        self.root_folder = root_folder
        self.wdir = wdir
        if initial:
            self.filename = self.filename.parent.relative_to(root_folder) / self.filename.name
        if not self.dest:
            self.path = self.root_folder / self.filename


@dataclass
class Match:
    """format info object mapped from siegfried output"""
    ns: str = ""
    id: str = ""
    formatname: str = ""  # Note this is different, in siegfried its format,
    version: str = ""
    mime: str = ""
    formatclass: str = ""  # Note this is different, in sigfried its class,
    basis: str = ""
    warning: str = ""


@dataclass
class Status:
    """status of the file: removed, pending for conversion or added"""
    removed: bool = False
    pending: bool = False
    added: bool = False


@dataclass
class LogTables:
    """table to store errors and warnings"""

    diagnostics: dict[StrEnum.name, list[SfInfo]] = field(default_factory=dict)
    errors: list[tuple[LogMsg, SfInfo]] = field(default_factory=list)

    def diagnostics_add(self, sfinfo: SfInfo, reason: StrEnum):
        if reason.name not in self.diagnostics:
            self.diagnostics[reason.name] = []
        self.diagnostics[reason.name].append(sfinfo)

    def dump_errors(self) -> list[SfInfo]:
        [el[1].processing_logs.append(el[0]) for el in self.errors]
        return [el[1] for el in self.errors]


@dataclass
class BasicAnalytics:

    filehashes: dict[str, list[Path]] = field(default_factory=dict)
    puid_unique: dict[str, list[SfInfo]] = field(default_factory=dict)
    siegfried_errors: list[SfInfo] = field(default_factory=list)
    total_size: dict[str, int] = field(default_factory=dict)
    presets: dict[str, str] = None
    blank: list = None

    def append(self, sfinfo: SfInfo):
        if sfinfo.processed_as:
            if sfinfo.filehash not in self.filehashes:
                self.filehashes[sfinfo.filehash] = [sfinfo.filename]
            else:
                self.filehashes[sfinfo.filehash].append(sfinfo.filename)
            if sfinfo.processed_as not in self.puid_unique:
                self.puid_unique[sfinfo.processed_as] = [sfinfo]
            else:
                self.puid_unique[sfinfo.processed_as].append(sfinfo)
        if sfinfo.errors:
            self.siegfried_errors.append(sfinfo)

    def sort_puid_unique_by_size(self, puid: str) -> None:
            self.puid_unique[puid] = sorted(self.puid_unique[puid], key=lambda x: x.filesize, reverse=False)



SFoutput: Type = Dict[str, Any]
"""
single file information output of siegfried (json)

has the following values among others

{
    "filename": "abs/path/to/file.ext",
    "matches": [
        {
            "id": "processed_as",
            "warning": "some warnings"
        }
    ]
}
"""
