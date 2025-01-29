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
    """default directory paths.
    WDIR: the working directory. it adds the string to the root_folder -> path/to/folder/to/identify_WORKINGDIR
    if the string contains a slash, it's treated as a path.
    REMOVED: folder name within WDIR to store the files that got removed from root_folder during processing.
    TEST: folder name within WDIR to store the outcome of testing policies
    PRESETS: path relative to the script root
    """
    WDIR = "WORKINGDIR"
    REMOVED = "_REMOVED"
    TEST = "_TEST"
    PRESETS = "presets"
    # do not change this
    FMT2EXT = "fileidentification/conf/fmt2ext.json"


class JsonOutput(StrEnum):
    POLICIES = "_policies.json"
    LOG = "_log.json"
    FAILED = "_failed.json"


# msg
class PolicyMsg(StrEnum):
    FALLBACK = f'fmt not detected, falling back on ext'
    NOTINPOLICIES = f'file format is not in policies. running strict mode: file removed'
    SKIPPED = "file format is not in policies, skipped"


class FileDiagnosticsMsg(StrEnum):
    EMPTYSOURCE = 'empty source'
    ERROR = f'file is corrupt: removed'
    WARNING = "file has warnings"
    EXTMISMATCH = "extension mismatch"


class FileProcessingMsg(StrEnum):
    PUIDFAIL = "failed to get fmt type"
    CONVFAILED = "conversion failed"
    NOTEXPECTEDFMT = "converted file does not match the expected fmt."
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
