from enum import StrEnum


# application settings
class DroidSigURL(StrEnum):
    """urls to fetch droid signature xml from national archives"""

    NALIST = "https://www.nationalarchives.gov.uk/aboutapps/pronom/droid-signature-files.htm"
    cdnNA = "https://cdn.nationalarchives.gov.uk/documents/DROID_SignatureFile_"


FMT2EXT = "fileidentification/definitions/fmt2ext.json"


class Bin(StrEnum):
    MAGICK = "magick"
    FFMPEG = "ffmpeg"
    SOFFICE = "soffice"
    # INCSCAPE = "inkscape"
    EMPTY = ""


class LibreOfficePath(StrEnum):
    Darwin = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    Linux = "libreoffice"


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
class PolicyMsg(StrEnum):
    FALLBACK = "fmt not detected, falling back on ext"
    NOTINPOLICIES = "file format is not in policies. running strict mode: file removed"
    SKIPPED = "file format is not in policies, skipped"


class FileDiagnosticsMsg(StrEnum):
    EMPTYSOURCE = "empty source"
    ERROR = "file is corrupt: removed"
    WARNING = "file has warnings"
    EXTMISMATCH = "extension mismatch"


class FileProcessingMsg(StrEnum):
    PUIDFAIL = "failed to get fmt type"
    CONVFAILED = "conversion failed"
    NOTEXPECTEDFMT = "converted file does not match the expected fmt."
    FAILEDMOVE = "failed to rsyc the file"


# file corrupt errors to parse from wrappers.wrappers.Ffmpeg when in verbose mode
class ErrMsgFF(StrEnum):
    ffmpeg1 = "Error opening input files"
    # ffmpeg2 = "A non-intra slice in an IDR NAL unit"


# reencode with ffmpeg as it can handle that error
class ErrMsgReencode(StrEnum):
    ffmpeg1 = "A non-intra slice in an IDR NAL unit"


# file corrupt errors to parse form wrappers.wrappers.ImageMagick
# there must be more... add them when encountered
class ErrMsgIM(StrEnum):
    magic1 = "identify: Cannot read"
    magic2 = "identify: Sanity check on directory count failed"
    magic3 = "identify: Failed to read directory"
    magic4 = "data: premature end of data segment"
