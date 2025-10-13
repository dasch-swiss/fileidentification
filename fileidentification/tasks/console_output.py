import math

from typer import colors, secho

from fileidentification.definitions.constants import FMT2EXT, FDMsg
from fileidentification.definitions.models import BasicAnalytics, LogMsg, LogTables, Mode, Policies


def print_siegfried_errors(ba: BasicAnalytics) -> None:
    if ba.siegfried_errors:
        secho("got the following errors from siegfried", bold=True)
        for sfinfo in ba.siegfried_errors:
            secho(f"{sfinfo.filename} \n{sfinfo.errors}", fg=colors.RED)


def print_fmts(puids: list[str], ba: BasicAnalytics, policies: Policies, mode: Mode) -> None:
    if mode.QUIET:
        return
    secho("\n----------- file formats -----------\n", bold=True)
    secho(
        f"{'no. of files': <13} | {'combined size': <14} | {'fmt type': <10} | {'policy': <10} | {'convert': <10} | {'format name'}",
        bold=True,
    )
    for puid in puids:
        bytes_size: int = 0
        for sfinfo in ba.puid_unique[puid]:
            bytes_size += sfinfo.filesize
        ba.total_size[puid] = bytes_size
        size = _format_bite_size(bytes_size)
        nbr, fmtname = len(ba.puid_unique[puid]), f"{FMT2EXT[puid]['name']}"
        if puid not in policies:
            pn = "missing"
            rm = "remove" if mode.STRICT else ""
            secho(f"{nbr: <13} | {size: <14} | {puid: <10} | {pn: <10} | {rm: <10} | {fmtname}", fg=colors.RED)
        if puid in policies and not policies[puid].accepted:
            ubin = policies[puid].bin
            pn = ""
            secho(f"{nbr: <13} | {size: <14} | {puid: <10} | {pn: <10} | {ubin: <10} | {fmtname}", fg=colors.YELLOW)
        if puid in policies and policies[puid].accepted:
            pn = ""
            if ba.blank and puid in ba.blank:
                pn = "blank"
            secho(f"{nbr: <13} | {size: <14} | {puid: <10} | {pn: <10} | {'': <10} | {fmtname}")


def print_diagnostic(log_tables: LogTables, mode: Mode) -> None:
    # lists all corrupt files with the respective errors thrown
    if log_tables.diagnostics:
        if FDMsg.ERROR.name in log_tables.diagnostics:
            secho("\n----------- errors -----------", bold=True)
            for sfinfo in log_tables.diagnostics[FDMsg.ERROR.name]:
                secho(f"\n{_format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}")
                _print_logs(sfinfo.processing_logs)
        if mode.VERBOSE and not mode.QUIET:
            if FDMsg.WARNING.name in log_tables.diagnostics:
                secho("\n----------- warnings -----------", bold=True)
                for sfinfo in log_tables.diagnostics[FDMsg.WARNING.name]:
                    secho(f"\n{_format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}")
                    _print_logs(sfinfo.processing_logs)
            if FDMsg.EXTMISMATCH.name in log_tables.diagnostics:
                secho("\n----------- extension missmatch -----------", bold=True)
                for sfinfo in log_tables.diagnostics[FDMsg.EXTMISMATCH.name]:
                    secho(f"\n{_format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}")
                    _print_logs(sfinfo.processing_logs)


def print_duplicates(ba: BasicAnalytics, mode: Mode) -> None:
    if mode.QUIET:
        return
    # pop uniques files
    [ba.filehashes.pop(k) for k in ba.filehashes.copy() if len(ba.filehashes[k]) == 1]
    if ba.filehashes:
        secho("\n----------- duplicates -----------", bold=True)
        for k in ba.filehashes:
            secho(f"\nmd5: {k} - files: ", bold=True)
            for path in ba.filehashes[k]:
                secho(f"{path}")
        secho("\n")


def print_processing_errors(log_tables: LogTables) -> None:
    if log_tables.errors:
        secho("\n----------- processing errors -----------", bold=True)
        for err in log_tables.errors:
            secho(f"\n{_format_bite_size(err[1].filesize): >10}    {err[1].filename}")
            _print_logs([err[0]])


def _print_logs(logs: list[LogMsg]) -> None:
    for log in logs:
        secho(f"{log.timestamp}    {log.name}:    {log.msg.replace('\n', ' ')}")


def print_msg(msg: str, quiet: bool) -> None:
    if not quiet:
        secho(msg)


def _format_bite_size(bytes_size: int) -> str:
    tmp = bytes_size / (1024**2)
    if math.ceil(tmp) > 1000:
        tmp = tmp / 1024
        if math.ceil(tmp) > 1000:
            tmp = tmp / 1024
            return f"{round(tmp, 3)} TB"
        return f"{round(tmp, 3)} GB"
    return f"{round(tmp, 3)} MB"
