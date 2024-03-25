import logging
import subprocess
import json
import shlex
from pathlib import Path
from typing import Any, Union


def sf_analyse(path: Union[str, Path]) -> list[dict[str, Any]]:
    """analyse a file or folder recursively, returns a list of files with the information
    gathered with siegfried in json"""
    res = subprocess.run(["sf", "-json", path], capture_output=True, text=True)
    res.check_returncode()
    res = json.loads(res.stdout)
    return res['files']


def ffmpeg_analyse_stream(input: str) -> None:
    """run the file in ffmpeg dropping frames instead of showing it, catch errors"""
    res = subprocess.run(f'ffmpeg -v error -i {shlex.quote(input)} -f null -', shell=True, capture_output=True, text=True)
    if res.stderr:
        msg = f'stream of {input} got errors \n{res.stderr}'
        # with open(f'{input}.error.log', 'w') as f:
        #     f.write(res.stderr)
        logging.warning(msg)
        print(f'WARNING: {msg}')
