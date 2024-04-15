import math
import hashlib
from pathlib import Path


def format_bite_size(bytes_size: int) -> str:

    tmp = bytes_size / (1024 ** 2)
    if math.ceil(tmp) > 1000:
        tmp = tmp / 1024
        if math.ceil(tmp) > 1000:
            tmp = tmp / 1024
            return f'{round(tmp, 3)} TB'
        return f'{round(tmp, 3)} GB'
    return f'{round(tmp, 3)} MB'


def get_hash(path: str | Path) -> hashlib.sha256:
    sha256 = hashlib.sha256()
    with open(path, "rb") as s:
        for chunk in iter(lambda: s.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
