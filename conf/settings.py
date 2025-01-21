from enum import StrEnum


# application settings
class SiegfriedConf(StrEnum):
    """siegfried parameters"""
    ALG = "sha256"
    MULTI = "256"


class Bin(StrEnum):
    MAGICK = "magick"
    FFMPEG = "ffmpeg"
    SOFFICE = "soffice"
    INCSCAPE = "inkscape"
    EMPTY = ""


class LibreOfficePath(StrEnum):
    Darwin = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    Linux = "libreoffice"


class LibreOfficePdfSettings(StrEnum):
    # it needs libreoffice v7.4 + for this to work
    version2a = ":writer_pdf_Export:{\"SelectPdfVersion\":{\"type\":\"long\",\"value\":\"2\"}}"
    version1a = ":writer_pdf_Export:{\"SelectPdfVersion\":{\"type\":\"long\",\"value\":\"1\"}}"


# paths
class PathsConfig(StrEnum):
    """default directory paths"""
    FAILED = "_FAILED"
    FMT2EXT = "conf/fmt2ext.json"
    WDIR = "_WORKINGDIR"
    TEST = "_TEST"
    PRESETS = "presets"


class FileOutput(StrEnum):
    POLICIES = "_policies.json"
    CHANGELOG = "_changeLog.json"
    TMPSTATE = "_changeLog.json.tmp"
    FAILED = "_failed.json"


# msg
class PolicyMsg(StrEnum):
    FALLBACK = f'fmt not detected, falling back on ext'
    NOTINPOLICIES = f'file format is not in policies. running strict mode: moved to {PathsConfig.FAILED}'
    SKIPPED = "file format is not in policies, skipped"


class FileDiagnosticsMsg(StrEnum):
    EMPTYSOURCE = 'empty source, file removed'
    ERROR = f'file is corrupt. moving it to {PathsConfig.FAILED}'
    WARNING = "file has warnings"
    EXTMISMATCH = "extension mismatch"


class FileProcessingErr(StrEnum):
    PUIDFAIL = "failed to get fmt type"
    CONVFAILED = "conversion failed"
    NOTEXPECTEDFMT = "converted file did not match the expected fmt"
    FAILEDMOVE = "failed to rsyc the file"


class ChangeLogErr(StrEnum):
    NOHASH = "hash not found, cannot verify the file"
    MODIFIED = "changelog got modified"
    NOFILE = "changelog not found"


# file corrupt errors to parse from wrappers.wrappers.Ffmpeg when in verbose mode
class ErrorMsgFF(StrEnum):
    ffmpeg1 = "Error opening input files"
    ffmpeg2 = "A non-intra slice in an IDR NAL unit"


# file corrupt errors to parse form wrappers.wrappers.ImageMagick
# there must be more... add them when encountered
class ErrorMsgIM(StrEnum):
    magic1 = "identify: Cannot read"
    magic2 = "identify: Sanity check on directory count failed"
    magic3 = "identify: Failed to read directory"
    magic4 = "data: premature end of data segment"
