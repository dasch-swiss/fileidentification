from pathlib import Path
import typer
from typing_extensions import Annotated
from conf.models import SfInfo
from conf.settings import FileOutput, PathsConfig
from fileidentification.wrappers import homebrew_packeges
from fileidentification.filehandling import FileHandler, Postprocessor, Mode
from fileidentification.output import RenderTables

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
                 "[with -d: it replaces the original files with the converted one]")] = False,
        policies_path: Annotated[Path, typer.Option("--policies-path", "-p",
            help="path to the json file with the policies")] = None,
        blank: Annotated[bool, typer.Option("--blank", "-b",
            help="create a blank policies.json based on the files in the dir")] = False,
        extend: Annotated[bool, typer.Option("--extend-policies", "-e",
            help="append filetypes found in files_dir to the given policies if they are missing in it")] = False,
        test_puid: Annotated[str, typer.Option("--test-filetype", "-tf",
            help="test a puid from the policies with a respective sample of the directory")] = None,
        test_policies: Annotated[bool, typer.Option("--test", "-t",
            help="test all file conversions from the policies with a respective sample of the directory")] = False,
        delete_original: Annotated[bool, typer.Option("--delete-original", "-d",
            help="when generating policies: it sets the keep_original flag to false (default true)."
                 "[with -c: the the keep_original flag in the policies is ignored and originals are deleted]")] = False,
        mode_strict: Annotated[bool, typer.Option("--strict", "-s",
            help="when generating policies: non default filetypes are not added as blank policies."
                 "when applying policies: moves the files that are not listed in the policies to folder FAILED.")] = False,
        mode_verbose: Annotated[bool, typer.Option("--verbose", "-v",
            help="catches more warnings on video and image files during the integrity tests")] = False,
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
    mode = Mode(DELETEORIGINAL=delete_original, STRICT=mode_strict, VERBOSE=mode_verbose, QUIET=mode_quiet)
    fh = FileHandler(mode=mode)

    # cleanup caveat, if cmd is run with flag --cleanup and files already converted (i.e. there's a changLog.json.tmp )
    if cleanup and Path(f'{files_dir}{FileOutput.TMPSTATE}').is_file():
        fh.manage_policies(files_dir, policies_path)
        fh.cleanup(files_dir, wdir)
        Postprocessor.dump_json(fh.log_tables.processingerr, files_dir, FileOutput.FAILED)
        raise typer.Exit()

    # save policies caveat
    if save_policies:
        Postprocessor.save_policies_from(files_dir)

    # generate a list of SfInfo objects out of the target folder and generate policies
    fh.load_sfinfos(files_dir, wdir)
    fh.manage_policies(files_dir, policies_path, blank, extend)

    # file integrity tests
    if integrity_tests:
        fh.integrity_tests()
    if not apply:
        Postprocessor.dump_json(fh.sfinfos, files_dir, FileOutput.TMPSTATE, sha256=True)

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
        fh.cleanup(files_dir, wdir, stack)
    else:
        Postprocessor.dump_json(fh.pinned2log, files_dir, FileOutput.CHANGELOG, sha256=True)
        Postprocessor.dump_json(stack, files_dir, FileOutput.TMPSTATE, sha256=True)

    # RenderTables.report2file(fh, files_dir)
    Postprocessor.dump_json(fh.log_tables.processingerr, files_dir, FileOutput.FAILED)


if __name__ == "__main__":
    typer.run(main)
