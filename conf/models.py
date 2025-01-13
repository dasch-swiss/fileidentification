from __future__ import annotations
from datetime import datetime
from typing import Type, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from conf.settings import FileProcessingErr, SiegfriedConf
from enum import StrEnum
from pathlib import Path



@dataclass
class LogMsg:
    name: str = None
    msg: str = None
    timestamp: str = field(default_factory=str)

    def __post_init__(self):
        self.timestamp = str(datetime.now())


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
    processed_as: Optional[str] = None
    codec_info: Optional[list[LogMsg]] = field(default_factory=list)
    processing_error: Optional[FileProcessingErr] = None
    processing_logs: Optional[list[LogMsg]] = field(default_factory=list)
    # siegfried output of original if converted
    derived_from: Optional[SfInfo] = None
    # paths, tmp items used during processing, they are not written out to final protocol
    relative_path: Optional[Path] = None
    files_dir: Optional[Path] = None
    wdir: Optional[Path] = None
    cu_table: Optional[CleanUpTable] = None

    def as_dict(self):
        """return the class as dict, with Path as string, None values skipped, recursiv for derived_from"""
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

        # optional values added during processing
        if self.processed_as:
            res['processed_as'] = self.processed_as
        if self.codec_info:
            res['codec_info'] = [{k: v for k, v in asdict(el).items()} for el in self.codec_info]
        if self.processing_logs:
            res['processing_logs'] = [{k: v for k, v in asdict(el).items()} for el in self.processing_logs]
        # temp values used during processing, getting removed at the end
        if self.cu_table:
            res['cu_table'] = self.cu_table.as_dict()

        if self.derived_from:
            res['derived_from'] = self.derived_from.as_dict()

        return res


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
class CleanUpTable:
    """
    table to store the postprocessing info about moving and deleting files and directories
    """
    filename: Path = None
    dest: Path = None
    delete_original: Path = None
    wdir: Path = None
    filehash: str = None
    relative_path: Path = None

    def as_dict(self):
        res = {}
        optional = {
            "filename": self.filename,
            "dest": self.dest,
            "delete_original": self.delete_original,
            "wdir": self.wdir,
            "relative_path": self.relative_path
        }
        [res.update({key: f'{value}'}) for key, value in optional.items() if value is not None]
        return res


@dataclass
class LogTables:
    """table to store errors and warnings"""

    policies: dict[StrEnum.name, list[SfInfo]] = field(default_factory=dict)
    diagnostics: dict[StrEnum.name, list[SfInfo]] = field(default_factory=dict)
    processingerr: dict[StrEnum.name, list[SfInfo]] = field(default_factory=dict)

    def append2policies(self, sfinfo: SfInfo, reason: StrEnum):
        if reason.name not in self.policies:
            self.policies[reason.name] = []
        self.policies[reason.name].append(sfinfo)

    def append2diagnostics(self, sfinfo: SfInfo, reason: StrEnum):
        if reason.name not in self.diagnostics:
            self.diagnostics[reason.name] = []
        self.diagnostics[reason.name].append(sfinfo)

    def append2processingerr(self, sfinfo: SfInfo, reason: StrEnum):
        if reason.name not in self.processingerr:
            self.processingerr[reason.name] = []
        self.processingerr[reason.name].append(sfinfo)


@dataclass
class BasicAnalytics:

    filehashes: dict[str, list[Path]] = field(default_factory=dict)
    puid_unique: dict[str, list[SfInfo]] = field(default_factory=dict)
    siegfried_errors: list[SfInfo] = field(default_factory=list)
    fmt2ext: dict = field(default_factory=dict)
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

    @staticmethod
    def sort_by_filesize(sfinfos: list[SfInfo]) -> list[SfInfo]:
            return sorted(sfinfos, key=lambda x: x.filesize, reverse=False)



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
