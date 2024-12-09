import typer
from pathlib import Path
from typing import List, Optional
from typing_extensions import Annotated
from conf.models import PathsConfig
import identify


def chained(
        files_dir: Annotated[Path, typer.Argument(help="path to the directory or file")],
        p: Annotated[Optional[List[Path]], typer.Option()] = None,
        tmp_dir: Annotated[Path, typer.Option("--working-dir", "-w",
            help="path to working dir where the processed files are stored")] = None
    ):

    # check path
    if not files_dir.exists():
        print(f'{files_dir} not found. exiting...')
        raise typer.Exit(1)

    # configure working dir
    wdir = Path(f'{files_dir}{PathsConfig.WDIR}')
    if tmp_dir:
        if not tmp_dir.exists():
            tmp_dir.mkdir()
        wdir = tmp_dir

    for policies in p:
        print(policies)
        identify.main(files_dir, tmp_dir=wdir, policies_path=policies, apply=True, mode_cleanup=True, mode_quiet=True)


if __name__ == "__main__":
    typer.run(chained)