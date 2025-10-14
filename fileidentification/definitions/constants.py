import json
from enum import StrEnum
from pathlib import Path
from typing import Any


# application settings
class DroidSigURL(StrEnum):
    """urls to fetch droid signature xml from national archives"""

    NALIST = "https://www.nationalarchives.gov.uk/aboutapps/pronom/droid-signature-files.htm"
    CDN = "https://cdn.nationalarchives.gov.uk/documents/DROID_SignatureFile_"


# dict that resolves the puid to possible ext and file format name
FMTJSN: Path = Path("fileidentification/definitions/fmt2ext.json")
FMT2EXT: dict[str, Any] = json.loads(FMTJSN.read_text())


class Bin(StrEnum):
    MAGICK = "magick"
    FFMPEG = "ffmpeg"
    SOFFICE = "soffice"
    # INCSCAPE = "inkscape"
    EMPTY = ""


class LOPath(StrEnum):
    """path where LibreOffice exec is according to os"""

    Darwin = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    Linux = "libreoffice"


# foldername for removed files (is in TMP_DIR)
RMV_DIR = "_REMOVED"


# it needs libreoffice v7.4 + for this to work, set to pdf/A version 2
PDFSETTINGS = ':writer_pdf_Export:{"SelectPdfVersion":{"type":"long","value":"2"}}'


CSVFIELDS = [
    "filename",
    "filesize",
    "md5",
    "modified",
    "errors",
    "processed_as",
    "media_info",
    "processing_logs",
    "status",
    "derived_from",
]


# msg


class PVErr(StrEnum):
    """policy validation errors"""

    SEMICOLON = "the char ';' is not an allowed in processing_args"
    MISS_CON = "your missing 'target_container' in policy"
    MISS_EXP = "your missing 'expected' in policy"
    MISS_BIN = "your missing bin in policy"


class PCMsg(StrEnum):
    """policy log messages"""

    FALLBACK = "fmt not detected, falling back on ext"
    NOTINPOLICIES = "file format is not in policies. running strict mode: file removed"
    SKIPPED = "file format is not in policies, skipped"


class FDMsg(StrEnum):
    """file diagnostic message"""

    EMPTYSOURCE = "empty source"
    ERROR = "file is corrupt: removed"
    WARNING = "file has warnings"
    EXTMISMATCH = "extension mismatch"


class FPMsg(StrEnum):
    """file processing message"""

    PUIDFAIL = "failed to get fmt type"
    CONVFAILED = "conversion failed"
    NOTEXPECTEDFMT = "converted file does not match the expected fmt."


# file corrupt errors to parse from wrappers.wrappers.Ffmpeg when in verbose mode
class ErrMsgFF(StrEnum):
    """text in log of ffmpeg that indicate the file is corrupt"""

    ffmpeg1 = "Error opening input files"
    # ffmpeg2 = "A non-intra slice in an IDR NAL unit"


class ErrMsgRE(StrEnum):
    """text in log for smaller errors that can be solved with re encoding the file"""

    ffmpeg1 = "A non-intra slice in an IDR NAL unit"


# file corrupt errors to parse form wrappers.wrappers.ImageMagick
# there must be more... add them when encountered
class ErrMsgIM(StrEnum):
    """text in log that indicate that the file is corrupt"""

    magic1 = "identify: Cannot read"
    magic2 = "identify: Sanity check on directory count failed"
    magic3 = "identify: Failed to read directory"
    magic4 = "data: premature end of data segment"
