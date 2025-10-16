import shutil
from pathlib import Path
from typing import Any

from typer import colors, secho

from fileidentification.definitions.constants import RMV_DIR
from fileidentification.definitions.models import FilePaths, LogMsg, LogTables, Policies, SfInfo


def remove(sfinfo: SfInfo, log_tables: LogTables) -> None:
    """Move a file from its sfinfo path to tmp dir / _REMOVED / ..."""
    dest: Path = sfinfo.tdir / RMV_DIR / sfinfo.filename
    if not dest.parent.exists():
        dest.parent.mkdir(parents=True)
    try:
        sfinfo.path.rename(dest)
        sfinfo.status.removed = True
    except OSError as e:
        secho(f"{e}", fg=colors.RED)
        log_tables.errors.append((LogMsg(name="filehandler", msg=str(e)), sfinfo))


def move_tmp(stack: list[SfInfo], policies: Policies, log_tables: LogTables, remove_original: bool) -> bool:
    write_logs: bool = False

    for sfinfo in stack:
        # if it has a dest, it needs to be moved
        if sfinfo.dest:
            write_logs = True
            # remove the original if its mentioned and flag it accordingly
            if policies[sfinfo.derived_from.processed_as].remove_original or remove_original:  # type: ignore[index, union-attr]
                derived_from = next(sfi for sfi in stack if sfi.filename == sfinfo.derived_from.filename)  # type: ignore[union-attr]
                if derived_from.path.is_file():
                    remove(derived_from, log_tables)
            # create absolute filepath
            abs_dest = sfinfo.root_folder / sfinfo.dest / sfinfo.filename.name
            # append hash to filename if the path already exists
            if abs_dest.is_file():
                abs_dest = Path(abs_dest.parent, f"{sfinfo.filename.stem}_{sfinfo.md5[:6]}{sfinfo.filename.suffix}")
            # move the file
            try:
                sfinfo.filename.rename(abs_dest)
                if sfinfo.filename.parent.is_dir():
                    shutil.rmtree(sfinfo.filename.parent)
                # set relative path in sfinfo.filename, set flags
                sfinfo.filename = sfinfo.dest / abs_dest.name
                sfinfo.status.added = True
                sfinfo.dest = None
            except OSError as e:
                secho(f"{e}", fg=colors.RED)
                log_tables.errors.append((LogMsg(name="filehandler", msg=str(e)), sfinfo))

    return write_logs


def set_filepaths(fp: FilePaths, config: dict[str, Any], root_folder: Path) -> None:
    if root_folder.is_file():
        root_folder = Path(f"{root_folder.parent}_{root_folder.stem}")
    fp.TMP_DIR = Path(config["paths"]["TMP_DIR"])
    if not fp.TMP_DIR.is_absolute():
        fp.TMP_DIR = Path(f"{root_folder}{fp.TMP_DIR}")
    fp.LOG_J = Path(config["paths"]["LOG_J"])
    if not fp.LOG_J.is_absolute():
        fp.LOG_J = Path(f"{root_folder}{fp.LOG_J}")
    fp.POLICIES_J = Path(config["paths"]["POLICIES_J"])
    if not fp.POLICIES_J.is_absolute():
        fp.POLICIES_J = Path(f"{root_folder}{fp.POLICIES_J}")
