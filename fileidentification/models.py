from __future__ import annotations
import re
import hashlib
from datetime import datetime, UTC
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from pathlib import Path
from fileidentification.conf.settings import PolicyMsg, FileDiagnosticsMsg


class LogMsg(BaseModel):
    name: str
    msg: str
    timestamp: datetime | None = None

    def model_post_init(self, __context):  # type: ignore
        if not self.timestamp:
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
    md5: str = Field(default_factory=str)
    matches: list = Field(default_factory=list)  # type: ignore
    # added during processing
    status: Status = Field(default_factory=Status)
    processed_as: str | None = None
    media_info: list[LogMsg] = Field(default_factory=list[LogMsg])
    processing_logs: list[LogMsg] = Field(default_factory=list[LogMsg])
    # if converted
    derived_from: SfInfo | None = None
    dest: Path | None = None
    # paths used during processing, they are not written out
    path: Path = Field(default_factory=Path, exclude=True)
    root_folder: Path = Field(default_factory=Path, exclude=True)
    wdir: Path = Field(default_factory=Path, exclude=True)

    def model_post_init(self, __context):  # type: ignore
        if not self.status:
            self.status = Status()
        if not self.processed_as:
            self.processed_as = self._fetch_puid()
        if not self.md5:
            self.md5 = get_md5(self.filename)

    def _fetch_puid(self) -> str | None:
        if self.matches:
            if self.matches[0]["id"] == "UNKNOWN":
                fmts = re.findall(r"(fmt|x-fmt)/([\d]+)", self.matches[0]["warning"])
                fmts = [f"{el[0]}/{el[1]}" for el in fmts]
                if fmts:
                    self.processing_logs.append(LogMsg(name="filehandler", msg=PolicyMsg.FALLBACK))
                    return fmts[0]  # type: ignore
                return None
            else:
                return self.matches[0]["id"]  # type: ignore
        return None

    def set_processing_paths(self, root_folder: Path, wdir: Path, initial: bool = False) -> None:
        if root_folder.is_file():
            root_folder = root_folder.parent
        self.root_folder = root_folder
        self.wdir = wdir
        if initial:
            self.filename = self.filename.parent.relative_to(root_folder) / self.filename.name
        if not self.dest:
            self.path = self.root_folder / self.filename


class LogOutput(BaseModel):
    files: list[SfInfo] | None = None
    errors: list[SfInfo] | None = None


@dataclass
class LogTables:
    """table to store errors and warnings"""

    diagnostics: dict[str, list[SfInfo]] = field(default_factory=dict)
    errors: list[tuple[LogMsg, SfInfo]] = field(default_factory=list)

    def diagnostics_add(self, sfinfo: SfInfo, fdgm: FileDiagnosticsMsg) -> None:
        if fdgm.name not in self.diagnostics:
            self.diagnostics[fdgm.name] = []
        self.diagnostics[fdgm.name].append(sfinfo)

    def dump_errors(self) -> list[SfInfo] | None:
        if self.errors:
            for el in self.errors:
                el[1].processing_logs.append(el[0])
            return [el[1] for el in self.errors]
        return None


@dataclass
class BasicAnalytics:
    filehashes: dict[str, list[Path]] = field(default_factory=dict)
    puid_unique: dict[str, list[SfInfo]] = field(default_factory=dict)
    siegfried_errors: list[SfInfo] = field(default_factory=list)
    total_size: dict[str, int] = field(default_factory=dict)
    blank: list[str] | None = None

    def append(self, sfinfo: SfInfo) -> None:
        if sfinfo.processed_as:
            if sfinfo.md5 not in self.filehashes:
                self.filehashes[sfinfo.md5] = [sfinfo.filename]
            else:
                self.filehashes[sfinfo.md5].append(sfinfo.filename)
            if sfinfo.processed_as not in self.puid_unique:
                self.puid_unique[sfinfo.processed_as] = [sfinfo]
            else:
                self.puid_unique[sfinfo.processed_as].append(sfinfo)
        if sfinfo.errors:
            self.siegfried_errors.append(sfinfo)

    def sort_puid_unique_by_size(self, puid: str) -> None:
        self.puid_unique[puid] = sorted(self.puid_unique[puid], key=lambda x: x.filesize, reverse=False)


def get_md5(path: str | Path) -> str:
    md5 = hashlib.md5()
    with open(path, "rb") as s:
        for chunk in iter(lambda: s.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()
