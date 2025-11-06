import json

from typer import colors, secho

from fileidentification.definitions.models import LogMsg, LogTables, Policies, SfInfo
from fileidentification.definitions.settings import FMT2EXT, Bin, ErrMsgRE, FDMsg, FPMsg
from fileidentification.tasks.os_tasks import remove
from fileidentification.wrappers.ffmpeg import ffmpeg_inspect
from fileidentification.wrappers.imagemagick import imagemagick_inspect


def inspect_file(sfinfo: SfInfo, policies: Policies, log_tables: LogTables, verbose: bool) -> None:

    resp: FDMsg | None = report_only(sfinfo, policies, log_tables, verbose)
    if resp == FDMsg.ERROR:
        remove(sfinfo, log_tables)
    if resp == FDMsg.EXTMISMATCH:
        if len(FMT2EXT[sfinfo.processed_as]["file_extensions"]) == 1:  # type: ignore[index]
            ext = "." + FMT2EXT[sfinfo.processed_as]["file_extensions"][-1]  # type: ignore[index]
            _rename(sfinfo, ext, log_tables)
        else:
            secho(f"\nWARNING: you should manually rename {sfinfo.filename}", fg=colors.YELLOW)
            secho(f"{sfinfo.processing_logs[0].msg}", fg=colors.YELLOW)


def _rename(sfinfo: SfInfo, ext: str, log_tables: LogTables) -> None:
    dest = sfinfo.path.with_suffix(ext)
    # if a file with same name and extension already there, append file hash to name
    if sfinfo.path.with_suffix(ext).is_file():
        dest = sfinfo.path.parent / f"{sfinfo.path.stem}_{sfinfo.md5[:6]}{ext}"
    try:
        sfinfo.path.rename(dest)
        msg = f"did rename {sfinfo.path.name} -> {dest.name}"
        sfinfo.path, sfinfo.filename = dest, dest.relative_to(sfinfo.root_folder)
        sfinfo.processing_logs.append(LogMsg(name="filehandler", msg=msg))
    except OSError as e:
        secho(f"{e}", fg=colors.RED)
        log_tables.errors.append((LogMsg(name="filehandler", msg=str(e)), sfinfo))


def _content_errors(sfinfo: SfInfo, policies: Policies, log_tables: LogTables, verbose: bool) -> bool:  # noqa: C901, PLR0912
    """
    Check if the file throws any error while opening or playing.
    Error logging is added to the SfInfo class, only return True if there are major errors
    :returns False if file is readable
    :param sfinfo the metadata of the file to analyse
    :param policies the policies
    :param log_tables the logtables
    :param verbose if true it does more detailed inspections
    """

    pbin = ""
    if sfinfo.processed_as in policies:
        pbin = policies[sfinfo.processed_as].bin
    # select bin out of mimetype if not specified in policies
    if pbin == "" and sfinfo.matches[0]["mime"] != "":  # noqa: SIM102
        if sfinfo.matches[0]["mime"].split("/")[0] in ["image", "audio", "video"]:
            mime = sfinfo.matches[0]["mime"].split("/")[0]
            pbin = Bin.MAGICK if mime == "image" else Bin.FFMPEG
            msg = f"bin not specified in policies, using {pbin} according to the file mimetype for probing"
            sfinfo.processing_logs.append(LogMsg(name="filehandler", msg=msg))

    # get the specs and errors
    match pbin:
        case Bin.FFMPEG:
            error, warning, specs = ffmpeg_inspect(sfinfo, verbose=verbose)
            if specs and not sfinfo.media_info:
                sfinfo.media_info.append(LogMsg(name=Bin.FFMPEG, msg=json.dumps(specs)))
            if warning:
                sfinfo.processing_logs.append(LogMsg(name=Bin.FFMPEG, msg=warning))
                # see if warning needs file to be re-encoded
                if any(msg in warning for msg in ErrMsgRE):
                    sfinfo.processing_logs.append(LogMsg(name="filehandler", msg="re-encoding the file"))
                    sfinfo.status.pending = True
        case Bin.MAGICK:
            error, warning, specs = imagemagick_inspect(sfinfo, verbose=verbose)  # type: ignore[assignment]
            if specs and not sfinfo.media_info:
                sfinfo.media_info.append(LogMsg(name=Bin.MAGICK, msg=specs))  # type: ignore[arg-type]
            if warning:
                sfinfo.processing_logs.append(LogMsg(name=Bin.MAGICK, msg=warning))
        case _:
            # returns False if bin is soffice or empty string (means no tests)
            # TODO: inspection for other files than Audio/Video/IMAGE
            return False

    if error:
        log_tables.diagnostics_add(sfinfo, FDMsg.ERROR)
        return True
    if warning:
        log_tables.diagnostics_add(sfinfo, FDMsg.WARNING)
        return False
    return False


def report_only(sfinfo: SfInfo, policies: Policies, log_tables: LogTables, verbose: bool) -> FDMsg | None:
    puid = sfinfo.processed_as
    if not puid:
        msg = LogMsg(name="filehandler", msg=f"{FPMsg.PUIDFAIL} for {sfinfo.filename}")
        log_tables.errors.append((msg, sfinfo))
        return None

    if sfinfo.errors == FDMsg.EMPTYSOURCE:
        log_tables.diagnostics_add(sfinfo, FDMsg.ERROR)
        return FDMsg.ERROR

    # case where there is an extension missmatch, rename the file if there is a unique ext
    if sfinfo.matches[0]["warning"] == FDMsg.EXTMISMATCH:
        msg_txt = f"expecting one of the following ext: {list(FMT2EXT[puid]['file_extensions'])}"
        sfinfo.processing_logs.append(LogMsg(name="filehandler", msg=msg_txt))
        log_tables.diagnostics_add(sfinfo, FDMsg.EXTMISMATCH)
        return FDMsg.EXTMISMATCH

    # check if the file throws any errors while open/processing it with the respective bin
    if _content_errors(sfinfo, policies, log_tables, verbose):
        return FDMsg.ERROR

    return None
