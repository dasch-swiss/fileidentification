from typing import Any

from typer import colors, secho

from fileidentification.definitions.constants import FileDiagnosticsMsg
from fileidentification.definitions.models import BasicAnalytics, LogMsg, LogTables, Policies
from fileidentification.helpers import format_bite_size


def print_siegfried_errors(ba: BasicAnalytics) -> None:
    if ba.siegfried_errors:
        print("got the following errors from siegfried")
        for sfinfo in ba.siegfried_errors:
            print(f"{sfinfo.filename} \n{sfinfo.errors}")


def print_fmts(puids: list[str], ba: BasicAnalytics, fmt2ext: dict[str, Any], policies: Policies, strict: bool) -> None:
    secho("\n----------- file formats -----------\n", bold=True)
    secho(
        f"{'no. of files': <13} | {'combined size': <14} | {'fmt type': <10} | {'policy': <10} | {'bin (associated program)': <25} | {'format name'}",
        bold=True,
    )
    for puid in puids:
        bytes_size: int = 0
        for sfinfo in ba.puid_unique[puid]:
            bytes_size += sfinfo.filesize
        ba.total_size[puid] = bytes_size
        size = format_bite_size(bytes_size)
        nbr, fmtname = len(ba.puid_unique[puid]), f"{fmt2ext[puid]['name']}"
        if puid not in policies:
            pn = "missing"
            rm = "remove" if strict else ""
            secho(f"{nbr: <13} | {size: <14} | {puid: <10} | {pn: <10} | {rm: <25} | {fmtname}", fg=colors.RED)
        if puid in policies and not policies[puid].accepted:
            ubin = policies[puid].bin
            pn = ""
            secho(f"{nbr: <13} | {size: <14} | {puid: <10} | {pn: <10} | {ubin: <25} | {fmtname}", fg=colors.YELLOW)
        if puid in policies and policies[puid].accepted:
            pn = ""
            if ba.blank and puid in ba.blank:
                pn = "blank"
            print(f"{nbr: <13} | {size: <14} | {puid: <10} | {pn: <10} | {'': <25} | {fmtname}")


def print_diagnostic(log_tables: LogTables, verbose: bool) -> None:
    # lists all corrupt files with the respective errors thrown
    if log_tables.diagnostics:
        if FileDiagnosticsMsg.ERROR.name in log_tables.diagnostics.keys():
            secho("\n----------- errors -----------", bold=True)
            for sfinfo in log_tables.diagnostics[FileDiagnosticsMsg.ERROR.name]:
                print(f"\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}")
                _print_logs(sfinfo.processing_logs)
        if verbose:
            if FileDiagnosticsMsg.WARNING.name in log_tables.diagnostics.keys():
                secho("\n----------- warnings -----------", bold=True)
                for sfinfo in log_tables.diagnostics[FileDiagnosticsMsg.WARNING.name]:
                    print(f"\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}")
                    _print_logs(sfinfo.processing_logs)
            if FileDiagnosticsMsg.EXTMISMATCH.name in log_tables.diagnostics.keys():
                secho("\n----------- extension missmatch -----------", bold=True)
                for sfinfo in log_tables.diagnostics[FileDiagnosticsMsg.EXTMISMATCH.name]:
                    print(f"\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}")
                    _print_logs(sfinfo.processing_logs)
            print("\n")


def print_duplicates(ba: BasicAnalytics) -> None:
    # pop uniques files
    [ba.filehashes.pop(k) for k in ba.filehashes.copy() if len(ba.filehashes[k]) == 1]
    if ba.filehashes:
        secho("\n----------- duplicates -----------", bold=True)
        for k in ba.filehashes:
            print(f"\nmd5: {k} - files: ")
            [print(f"{path}") for path in ba.filehashes[k]]
        print("\n")


def print_processing_errors(log_tables: LogTables) -> None:
    if log_tables.errors:
        secho("\n----------- processing errors -----------", bold=True)
        for err in log_tables.errors:
            print(f"\n{format_bite_size(err[1].filesize): >10}    {err[1].filename}")
            _print_logs([err[0]])


def _print_logs(logs: list[LogMsg]) -> None:
    for log in logs:
        print(f"{log.timestamp}    {log.name}:    {log.msg.replace('\n', ' ')}")
