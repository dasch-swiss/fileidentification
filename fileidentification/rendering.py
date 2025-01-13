import sys
from pathlib import Path
from datetime import datetime
from typer import secho, colors
from conf.settings import SiegfriedConf, FileDiagnosticsMsg, PolicyMsg, PathsConfig
from fileidentification.helpers import format_bite_size


class RenderTables:

    @staticmethod
    def print_siegfried_errors(fh):
        if fh.ba.siegfried_errors:
            print('got the following errors from siegfried')
            for sfinfo in fh.ba.siegfried_errors:
                print(f'{sfinfo.filename} \n{sfinfo.errors} {sfinfo.processing_logs}')

    @staticmethod
    def print_duplicates(fh):
        """prints out the used hash algorithm, the hash and the files that have the same hash"""
        # pop uniques files
        [fh.ba.filehashes.pop(k) for k in fh.ba.filehashes.copy() if len(fh.ba.filehashes[k]) == 1]
        if fh.ba.filehashes:
            print("\n----------- duplicates -----------")
            for k in fh.ba.filehashes:
                print(f'\n{SiegfriedConf.ALG}: {k} - files: ')
                [print(f'{path}') for path in fh.ba.filehashes[k]]

    @staticmethod
    def print_fileformats(fh, puids: list[str]):
        print("\n----------- fileformats -----------")
        print(f"{'no. of files': <13} | {'combined size': <14} | {'fmt type': <10} | {'policy': <10} | {'bin (associated program)': <25} | {'format name'}")
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
    def print_diagnostic_table(fh) -> None:
        """lists all corrupt files with the respective errors thrown"""
        if fh.log_tables.diagnostics:
            if FileDiagnosticsMsg.ERROR.name in fh.log_tables.diagnostics.keys():
                print("\n----------- errors -----------")
                for sfinfo in fh.log_tables.diagnostics[FileDiagnosticsMsg.ERROR.name]:
                    print(f'\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}')
                    print(sfinfo.processing_logs)
            if fh.mode.VERBOSE:
                if FileDiagnosticsMsg.WARNING.name in fh.log_tables.diagnostics.keys():
                    print("\n----------- warnings -----------")
                    for sfinfo in fh.log_tables.diagnostics[FileDiagnosticsMsg.WARNING.name]:
                        print(f'\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}')
                        print(sfinfo.processing_logs)
                if FileDiagnosticsMsg.EXTMISMATCH.name in fh.log_tables.diagnostics.keys():
                    print("\n----------- extension missmatch -----------")
                    for sfinfo in fh.log_tables.diagnostics[FileDiagnosticsMsg.EXTMISMATCH.name]:
                        print(f'\n{format_bite_size(sfinfo.filesize): >10}    {sfinfo.filename}')
                        print(sfinfo.processing_logs)
                print("\n")

    @staticmethod
    def print_policies_errors(fh) -> None:

        if fh.log_tables.policies[PolicyMsg.NOTINPOLICIES]:
            print(f'--> running in strict mode: moved the following files to {PathsConfig.FAILED}')
            [print(f'{el.processed_as: <10}{el.filename}') for el in fh.log_tables.policies[PolicyMsg.NOTINPOLICIES]]
        if fh.log_tables.policies[PolicyMsg.SKIPPED]:
            print(f'--> skipped these files, their fmt is not in policies:')
            [print(f'{el.processed_as: <10}{el.filename}') for el in fh.log_tables.policies[PolicyMsg.NOTINPOLICIES]]


    @staticmethod
    def print_processing_table(fh) -> None:
        # TODO
        pass

    @staticmethod
    def report2file(fh, path: Path) -> None:
        default = sys.stdout
        with open(f'{path}_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt', 'a') as f:
            sys.stdout = f
            RenderTables.print_siegfried_errors(fh)
            RenderTables.print_fileformats(fh, puids=[el for el in fh.ba.puid_unique])
            RenderTables.print_duplicates(fh)
            RenderTables.print_diagnostic_table(fh)
            sys.stdout = default

        print(f'report written to {path}_report.txt')
