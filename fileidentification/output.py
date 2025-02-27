from typer import secho, colors
from fileidentification.conf.settings import SiegfriedConf, FileDiagnosticsMsg
from fileidentification.conf.models import LogMsg
from fileidentification.helpers import format_bite_size


class Output:

    @staticmethod
    def print_siegfried_errors(fh):
        if fh.ba.siegfried_errors:
            print('got the following errors from siegfried')
            for sfinfo in fh.ba.siegfried_errors:
                print(f'{sfinfo.filename} \n{sfinfo.errors} {Output._print_logs(sfinfo.processing_logs)}')


    @staticmethod
    def print_fileformats(fh, puids: list[str]):
        secho("\n----------- file formats -----------\n", bold=True)
        secho(f"{'no. of files': <13} | {'combined size': <14} | {'fmt type': <10} | {'policy': <10} | {'bin (associated program)': <25} | {'format name'}", bold=True)
        for puid in puids:
            bytes_size: int = 0
            for sfinfo in fh.ba.puid_unique[puid]:
                bytes_size += sfinfo.filesize
            fh.ba.total_size[puid] = bytes_size
            size = format_bite_size(bytes_size)
            nbr, fmtname, = len(fh.ba.puid_unique[puid]), f'{fh.fmt2ext[puid]["name"]}'
            if fh.mode.STRICT and puid not in fh.policies:
                pn = "strict"
                secho(f'{nbr: <13} | {size: <14} | {puid: <10} | {pn: <10} | {"": <25} | {fmtname}', fg=colors.RED)
            if puid in fh.policies and not fh.policies[puid]['accepted']:
                bin = fh.policies[puid]['bin']
                pn = ""
                if fh.ba.presets and puid in fh.ba.presets:
                   pn = fh.ba.presets[puid]
                secho(f'{nbr: <13} | {size: <14} | {puid: <10} | {pn: <10} | {bin: <25} | {fmtname}', fg=colors.YELLOW)
            if puid in fh.policies and fh.policies[puid]['accepted']:
                pn = ""
                if fh.ba.blank and puid in fh.ba.blank:
                    pn = "blank"
                if fh.ba.presets and puid in fh.ba.presets:
                   pn = fh.ba.presets[puid]
                print(f'{nbr: <13} | {size: <14} | {puid: <10} | {pn: <10} | {"": <25} | {fmtname}')

    @staticmethod
    def print_diagnostic(fh) -> None:

        # lists all corrupt files with the respective errors thrown
        if fh.log_tables.diagnostics:
            if FileDiagnosticsMsg.ERROR.name in fh.log_tables.diagnostics.keys():
                secho("\n----------- errors -----------", bold=True)
                for sfinfo in fh.log_tables.diagnostics[FileDiagnosticsMsg.ERROR.name]:
                    print(f'\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}')
                    Output._print_logs(sfinfo.processing_logs)
            if fh.mode.VERBOSE:
                if FileDiagnosticsMsg.WARNING.name in fh.log_tables.diagnostics.keys():
                    secho("\n----------- warnings -----------", bold=True)
                    for sfinfo in fh.log_tables.diagnostics[FileDiagnosticsMsg.WARNING.name]:
                        print(f'\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}')
                        Output._print_logs(sfinfo.processing_logs)
                if FileDiagnosticsMsg.EXTMISMATCH.name in fh.log_tables.diagnostics.keys():
                    secho("\n----------- extension missmatch -----------", bold=True)
                    for sfinfo in fh.log_tables.diagnostics[FileDiagnosticsMsg.EXTMISMATCH.name]:
                        print(f'\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}')
                        Output._print_logs(sfinfo.processing_logs)
                print("\n")

    @staticmethod
    def print_duplicates(fh) -> None:
        # pop uniques files
        [fh.ba.filehashes.pop(k) for k in fh.ba.filehashes.copy() if len(fh.ba.filehashes[k]) == 1]
        if fh.ba.filehashes:
            secho("\n----------- duplicates -----------", bold=True)
            for k in fh.ba.filehashes:
                print(f'\n{SiegfriedConf.ALG}: {k} - files: ')
                [print(f'{path}') for path in fh.ba.filehashes[k]]
            print("\n")


    @staticmethod
    def _print_logs(logs: list[LogMsg]):
        for l in logs:
            print(f'{l.timestamp}    {l.name}:    {l.msg.replace("\n", " ")}')

    @staticmethod
    def print_processing_errors(fh) -> None:
        if fh.log_tables.errors:
            secho("\n----------- processing errors -----------", bold=True)
            for err in fh.log_tables.errors:
                print(f'\n{format_bite_size(err[1].filesize): >10}    {err[1].filename}')
                Output._print_logs([err[0]])
