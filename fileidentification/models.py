from __future__ import annotations
import re
from datetime import datetime, UTC
from typing import Type, Dict, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from enum import StrEnum
from pathlib import Path
from fileidentification.conf.settings import SiegfriedConf, PolicyMsg


class LogMsg(BaseModel):
    name: str
    msg: str
    timestamp: datetime | None = None

    def model_post_init(self, __context):
        self.timestamp = datetime.now(UTC)


class Status(BaseModel):
    """status of the file: removed, pending for conversion or added"""
    removed: bool = False
    pending: bool = False
    added: bool = False


class SfInfo(BaseModel):
    """file info object mapped from siegfried output, gets extended while processing."""
    # output from siegfried
    filename: Path
    filesize: int
    modified: str
    errors: str
    filehash: str = Field(alias=SiegfriedConf.ALG)
    matches: list | None = None
    # added during processing
    status: Status | None = None
    processed_as: str | None = None
    media_info: list[LogMsg] = Field(default_factory=list[LogMsg])
    processing_logs: list[LogMsg] = Field(default_factory=list[LogMsg])
    # if converted
    derived_from: SfInfo | None = None
    dest: Path | None = None
    # paths used during processing, they are not written out
    _path: Path | None = None
    _root_folder: Path | None = None
    _wdir: Path | None = None

    def model_post_init(self, __context):
        if not self.status:
            self.status = Status()
        if not self.processed_as:
            self.processed_as = self._fetch_puid()

    def _fetch_puid(self) -> str | None:
        if self.matches[0]['id'] == 'UNKNOWN':
            fmts = re.findall(r"(fmt|x-fmt)/([\d]+)", self.matches[0]['warning'])
            fmts = [f'{el[0]}/{el[1]}' for el in fmts]
            if fmts:
                self.processing_logs.append(LogMsg(name='filehandler', msg=PolicyMsg.FALLBACK))
                return fmts[0]
            return None
        else:
            return self.matches[0]['id']

    def set_processing_paths(self, root_folder: Path, wdir: Path, initial=False):

        if root_folder.is_file():
            root_folder = root_folder.parent
        self._root_folder = root_folder
        self._wdir = wdir
        if initial:
            self.filename = self.filename.parent.relative_to(root_folder) / self.filename.name
        if not self.dest:
            self._path = self._root_folder / self.filename


class LogOutput(BaseModel):
    files: list[SfInfo] = None
    errors: list[SfInfo] | None = None


@dataclass
class LogTables:
    """table to store errors and warnings"""

    diagnostics: dict[StrEnum.name, list[SfInfo]] = field(default_factory=dict)
    errors: list[tuple[LogMsg, SfInfo]] = field(default_factory=list)

    def diagnostics_add(self, sfinfo: SfInfo, reason: StrEnum):
        if reason.name not in self.diagnostics:
            self.diagnostics[reason.name] = []
        self.diagnostics[reason.name].append(sfinfo)

    def dump_errors(self) -> list[SfInfo] | None:
        if self.errors:
            [el[1].processing_logs.append(el[0]) for el in self.errors]
            return [el[1] for el in self.errors]
        return


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
