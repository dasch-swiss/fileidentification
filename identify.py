from pathlib import Path
import typer
from typing_extensions import Annotated
from conf.models import SfInfo
from conf.settings import FileOutput, PathsConfig
from fileidentification.wrappers import homebrew_packeges
from fileidentification.filehandling import FileHandler, Postprocessor, Mode, save_policies_from
from fileidentification.rendering import RenderTables

# check for the dependencies
homebrew_packeges.check()


def main(
        files_dir: Annotated[Path, typer.Argument(help="path to the directory or file")],
        tmp_dir: Annotated[Path, typer.Option("--working-dir", "-w",
            help="path to working dir where the processed files are stored")] = None,
        integrity_tests: Annotated[bool, typer.Option("--integrity-tests", "-i",
            help="apply the [pinned] conversions")] = False,
        apply: Annotated[bool, typer.Option("--apply", "-a", help="apply the [pinned] conversions")] = False,
        cleanup: Annotated[bool, typer.Option("--cleanup", "-c",
            help="removes all temporary items and moves the converted files to the folder of its original file"
                 "[with -d also passed: it replaces the original files with the converted one]")] = False,
        policies_path: Annotated[Path, typer.Option("--policies-path", "-p",
            help="path to the json file with the policies")] = None,
        blank: Annotated[bool, typer.Option("--blank", "-b",
            help="create a blank policies.json based on the files in the dir")] = False,
        extend: Annotated[bool, typer.Option("--extend-policies", "-e",
            help="append filetypes found in files_dir to the given policies if they are missing in it")] = False,
        test_puid: Annotated[str, typer.Option("--test-filetype", "-tf",
            help="test a puid from the policies with a respective sample of the directory")] = None,
        test_policies: Annotated[bool, typer.Option("--test", "-t",
            help="test all file conversions from the policies with a respective sample of the directory")] = None,
        delete_original: Annotated[bool, typer.Option("--delete-original", "-d",
            help="when generating policies: it sets the keep_original flag to true (default false)."
                 "[with -c also passed: the flag in the policies is ignored and originals are not deleted]")] = False,
        mode_strict: Annotated[bool, typer.Option("--strict", "-s",
            help="when generating policies: non default filetypes are not added as blank policies."
                 "when applying policies: moves the files that are not listed in the policies to folder FAILED.")] = False,
        mode_verbose: Annotated[bool, typer.Option("--verbose", "-v",
            help="lists every file in report, every minor error and does deeper file inspection on video files")] = False,
        mode_quiet: Annotated[bool, typer.Option("--quiet", "-q",
            help="just print errors and warnings")] = False,
        save_policies: Annotated[bool, typer.Option("--save-policies", "-S",
            help="copy the local policies to conf/presets/")] = False
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

    # the file handler with the respective mode,
    mode = Mode(ADD=False if delete_original else True, STRICT=mode_strict, VERBOSE=mode_verbose, QUIET=mode_quiet)
    fh = FileHandler(mode=mode)

    # cleanup caveat, if cmd is run with flag --cleanup and files already converted (i.e. there's a changLog.json.tmp )
    if cleanup and Path(f'{files_dir}{FileOutput.TMPSTATE}').is_file():
        fh.clean_up(files_dir, wdir)
        raise typer.Exit()

    # save policies caveat
    if save_policies:
        save_policies_from(files_dir)

    # generate a list of SfInfo objects out of the target folder and generate policies
    fh.gen_sfinfos(files_dir, wdir)
    fh.manage_policies(files_dir, policies_path, blank, extend)

    # file integrity tests
    if integrity_tests:
        fh.integrity_tests()

    # policies testing
    if test_puid:
        fh.test_policies(files_dir, wdir, puid=test_puid)
    if test_policies:
        fh.apply_policies()
        fh.test_policies(files_dir, wdir)

    # apply policies
    stack: list[SfInfo] = []
    if apply:
        fh.apply_policies()
        stack = fh.convert()

    # cleanup
    if cleanup:
        fh.clean_up(files_dir, wdir, stack)
    else:
        Postprocessor.dump_json(fh.pinned2log, files_dir, FileOutput.CHANGELOG, sha256=True)
        Postprocessor.dump_json(stack, files_dir, FileOutput.TMPSTATE, sha256=True)

    RenderTables.report2file(fh, files_dir)


if __name__ == "__main__":
    typer.run(main)
