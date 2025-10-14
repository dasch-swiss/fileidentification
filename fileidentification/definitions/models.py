import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from fileidentification.definitions.constants import Bin, FDMsg, PCMsg, PVErr


class LogMsg(BaseModel):
    name: str
    msg: str
    timestamp: datetime | None = None

    def model_post_init(self, context: Any, /) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC)


class Status(BaseModel):
    """status of the file: removed, pending for conversion or added"""

    removed: bool = False
    pending: bool = False
    added: bool = False


# main metadata object where information is stored and added
class SfInfo(BaseModel):
    """file info object mapped from siegfried output, gets extended while processing."""

    # output from siegfried
    filename: Path
    filesize: int
    modified: str
    errors: str
    md5: str = Field(default_factory=str)
    matches: list[dict[str, Any]] = Field(default_factory=list)
    # added during processing
    status: Status = Field(default_factory=Status)
    processed_as: str | None = None
    media_info: list[LogMsg] = Field(default_factory=list[LogMsg])
    processing_logs: list[LogMsg] = Field(default_factory=list[LogMsg])
    # if converted
    derived_from: Self | None = None
    dest: Path | None = None
    # paths used during processing, they are not written out
    path: Path = Field(default_factory=Path, exclude=True)
    root_folder: Path = Field(default_factory=Path, exclude=True)
    tdir: Path = Field(default_factory=Path, exclude=True)

    def model_post_init(self, context: Any, /) -> None:
        if not self.status:
            self.status = Status()
        if not self.processed_as:
            self.processed_as = self._fetch_puid()
        if not self.md5:
            self.md5 = get_md5(self.filename)

    def _fetch_puid(self) -> str | None:
        if self.matches:
            if self.matches[0]["id"] == "UNKNOWN":
                # check whether pygfried suggest puid according to extension
                fmts = re.findall(r"(fmt|x-fmt)/([\d]+)", self.matches[0]["warning"])
                fmts_s: list[str] = [f"{el[0]}/{el[1]}" for el in fmts]
                if fmts:
                    self.processing_logs.append(LogMsg(name="filehandler", msg=PCMsg.FALLBACK))
                    return fmts_s[0]
                return None
            puid: str = self.matches[0]["id"]
            return puid
        return None

    def set_processing_paths(self, root_folder: Path, tdir: Path, initial: bool) -> None:
        if root_folder.is_file():
            root_folder = root_folder.parent
        self.root_folder = root_folder
        self.tdir = tdir
        if initial:
            self.filename = self.filename.parent.relative_to(root_folder) / self.filename.name
        if not self.dest:
            self.path = self.root_folder / self.filename


class LogOutput(BaseModel):
    files: list[SfInfo] | None = None
    errors: list[SfInfo] | None = None


class LogTables(BaseModel):
    """table to store errors and warnings"""

    diagnostics: dict[str, list[SfInfo]] = Field(default_factory=dict)
    errors: list[tuple[LogMsg, SfInfo]] = Field(default_factory=list)

    def diagnostics_add(self, sfinfo: SfInfo, fdgm: FDMsg) -> None:
        if fdgm.name not in self.diagnostics:
            self.diagnostics[fdgm.name] = []
        self.diagnostics[fdgm.name].append(sfinfo)

    def dump_errors(self) -> list[SfInfo] | None:
        if self.errors:
            for el in self.errors:
                el[1].processing_logs.append(el[0])
            return [el[1] for el in self.errors]
        return None


class BasicAnalytics(BaseModel):
    filehashes: dict[str, list[Path]] = Field(default_factory=dict)
    puid_unique: dict[str, list[SfInfo]] = Field(default_factory=dict)
    siegfried_errors: list[SfInfo] = Field(default_factory=list)
    total_size: dict[str, int] = Field(default_factory=dict)
    blank: list[str] | None = None

    def append(self, sfinfo: SfInfo) -> None:
        if sfinfo.processed_as:
            if sfinfo.md5 not in self.filehashes:
                self.filehashes[sfinfo.md5] = []
            self.filehashes[sfinfo.md5].append(sfinfo.filename)
            if sfinfo.processed_as not in self.puid_unique:
                self.puid_unique[sfinfo.processed_as] = []
            self.puid_unique[sfinfo.processed_as].append(sfinfo)
        if sfinfo.errors:
            self.siegfried_errors.append(sfinfo)

    def sort_puid_unique_by_size(self, puid: str) -> None:
        self.puid_unique[puid] = sorted(self.puid_unique[puid], key=lambda x: x.filesize, reverse=False)


# models for policies
class PolicyParams(BaseModel):
    format_name: str = Field(default_factory=str)
    bin: str = Field(default="")
    accepted: bool = Field(default=True)
    target_container: str = Field(default="")
    processing_args: str = Field(default="")
    expected: list[str] = Field(default=[""])
    remove_original: bool = Field(default=False)

    @field_validator("bin", mode="after")
    @classmethod
    def allowed_bin(cls, value: str) -> str:
        if value not in Bin:
            raise ValueError(f"{value} is not an allowed bin")  # noqa: EM102, TRY003
        return value

    @field_validator("processing_args", mode="after")
    @classmethod
    def allowed_args(cls, value: str) -> str:
        if ";" in value:
            raise ValueError(PVErr.SEMICOLON)
        return value

    @model_validator(mode="after")
    def assert_conv_args(self) -> Self:
        if self.accepted is False:
            if self.target_container == "":
                raise ValueError(PVErr.MISS_CON)
            if self.expected == [""]:
                raise ValueError(PVErr.MISS_EXP)
            if self.bin == "":
                raise ValueError(PVErr.MISS_BIN)
        return self


Policies = dict[str, PolicyParams]


class PoliciesFile(BaseModel):
    name: Path = Field(default_factory=Path)
    comment: str = Field(default_factory=str)
    policies: Policies = Field(default_factory=Policies)


# Settings for the Filehandler Class
class Mode(BaseModel):
    """
    the different modes for the FileHandler.
    REMOVEORIGINAL: bool, whether to remove the original files of the files that got converted
    VERBOSE: bool, do verbose analysis of video and image files
    STRICT: bool, move files that are not listed in policies to FAILED instead of skipping them
    QUIET: bool, just print warnings and errors
    """

    REMOVEORIGINAL: bool = False
    VERBOSE: bool = False
    STRICT: bool = False
    QUIET: bool = False


class FilePaths(BaseModel, validate_assignment=True):
    TMP_DIR: Path = Field(default_factory=Path)
    POLICIES_J: Path = Field(default_factory=Path)
    LOG_J: Path = Field(default_factory=Path)


def get_md5(path: str | Path) -> str:
    md5 = hashlib.md5()  # noqa: S324
    with open(path, "rb") as s:  # noqa: PTH123
        for chunk in iter(lambda: s.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()


def sfinfo2csv(sfinfo: SfInfo) -> dict[str, str | int]:
    res: dict[str, str | int] = {
        "filename": f"{sfinfo.filename}",
        "filesize": sfinfo.filesize,
        "modified": sfinfo.modified,
        "errors": sfinfo.errors,
        "md5": sfinfo.md5,
    }
    if sfinfo.status.pending:
        res.update({"status": "pending"})
    if sfinfo.status.added:
        res.update({"status": "added"})
    if sfinfo.status.removed:
        res.update({"status": "removed"})
    if sfinfo.processed_as:
        res["processed_as"] = sfinfo.processed_as
    if sfinfo.media_info:
        res["media_info"] = sfinfo.media_info[0].msg
    if sfinfo.processing_logs:
        res["processing_logs"] = " ; ".join([el.msg for el in sfinfo.processing_logs if el.name == "filehandler"])
    if sfinfo.derived_from:
        res["derived_from"] = f"{sfinfo.derived_from.filename}"
    return res
