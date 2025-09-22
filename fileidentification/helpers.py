import math
from fileidentification.models import SfInfo
from typing import Any


def format_bite_size(bytes_size: int) -> str:

    tmp = bytes_size / (1024 ** 2)
    if math.ceil(tmp) > 1000:
        tmp = tmp / 1024
        if math.ceil(tmp) > 1000:
            tmp = tmp / 1024
            return f'{round(tmp, 3)} TB'
        return f'{round(tmp, 3)} GB'
    return f'{round(tmp, 3)} MB'


def sfinfo2csv(sfinfo: SfInfo) -> dict[str, Any]:
    res = {"filename": f'{sfinfo.filename}',
           "filesize": sfinfo.filesize,
           "modified": sfinfo.modified,
           "errors": sfinfo.errors,
           "md5": sfinfo.md5}
    if sfinfo.status.pending:
        res.update({"status": "pending"})
    if sfinfo.status.added:
        res.update({"status": "added"})
    if sfinfo.status.removed:
        res.update({"status": "removed"})
    if sfinfo.processed_as:
        res['processed_as'] = sfinfo.processed_as
    if sfinfo.media_info:
        res['media_info'] = sfinfo.media_info[0].msg
    if sfinfo.processing_logs:
        res['processing_logs'] = " ; ".join([el.msg for el in sfinfo.processing_logs if el.name == "filehandler"])
    if sfinfo.derived_from:
        res['derived_from'] = sfinfo.derived_from.filename
    return res
