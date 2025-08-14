from pathlib import Path
import typer
from typing_extensions import Annotated
from fileidentification.filehandling import FileHandler


def main(
        root_folder: Annotated[Path, typer.Argument(help="path to the directory or file")],
        tmp_dir: Annotated[Path, typer.Option("--working-dir", "-w",
            help="path to working dir where the processed files are stored")] = None,
        integrity_tests: Annotated[bool, typer.Option("--integrity-tests", "-i",
            help="do integrity tests on the files in the selected folder")] = False,
        apply: Annotated[bool, typer.Option("--apply", "-a", help="apply the policies and convert the pending files")] = False,
        convert: Annotated[bool, typer.Option("--convert", help="re-convert failed pending files")] = False,
        remove_tmp: Annotated[bool, typer.Option("--remove-tmp", "-r",
            help="removes all temporary items and moves the converted files to the folder of its original file"
                 "[with -x: it replaces the original files with the converted one]")] = False,
        policies_path: Annotated[Path, typer.Option("--policies-path", "-p",
            help="path to the json file with the policies")] = None,
        blank: Annotated[bool, typer.Option("--blank", "-b",
            help="create a blank policies.json based on the files in the dir")] = False,
        extend: Annotated[bool, typer.Option("--extend-policies", "-e",
            help="append filetypes found in root_folder to the given policies if they are missing in it")] = False,
        test_puid: Annotated[str, typer.Option("--test-filetype", "-tf",
            help="test a puid from the policies with a respective sample of the directory")] = None,
        test_policies: Annotated[bool, typer.Option("--test", "-t",
            help="test all file conversions from the policies with a respective sample of the directory")] = False,
        remove_original: Annotated[bool, typer.Option("--remove-original", "-x",
            help="when generating policies: it sets the remove_original flag to true (default false)."
                 "[with -r: the the remove_original flag in the policies is ignored and originals are removed]")] = False,
        mode_strict: Annotated[bool, typer.Option("--strict", "-s",
            help="when generating policies: non default filetypes are not added as blank policies."
                 "when applying policies: moves the files that are not listed in the policies to folder _REMOVED.")] = False,
        mode_verbose: Annotated[bool, typer.Option("--verbose", "-v",
            help="catches more warnings on video and image files during the integrity tests")] = False,
        mode_quiet: Annotated[bool, typer.Option("--quiet", "-q",
            help="just print errors and warnings")] = False,
        to_csv: Annotated[bool, typer.Option("--csv", help="get a csv out of the log.json")] = False
    ):

    fh = FileHandler()
    fh.run(root_folder=root_folder, tmp_dir=tmp_dir,
           integrity_tests=integrity_tests, apply=apply, convert=convert, remove_tmp=remove_tmp,
           policies_path=policies_path, blank=blank, extend=extend, test_puid=test_puid, test_policies=test_policies,
           remove_original=remove_original, mode_strict=mode_strict, mode_verbose=mode_verbose, mode_quiet=mode_quiet,
           to_csv=to_csv)


if __name__ == "__main__":
    typer.run(main)
