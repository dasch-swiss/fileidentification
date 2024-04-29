import shutil
from pathlib import Path
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing_extensions import Annotated
from conf.models import SfInfo, FileOutput, PathsConfig
from fileidentification.wrappers import homebrew_packeges
from fileidentification.wrappers.wrappers import Siegfried as Sf
from fileidentification.parser.parser import SFParser
from fileidentification.filehandling import (FileHandler, Postprocessor, Mode, RenderTables as Rt,
                                             parse_protocol, save_policies_from, clean_up)

# check for the dependencies
homebrew_packeges.check()


def main(
        files_dir: Annotated[Path, typer.Argument(help="path to the directory or file")],
        apply: Annotated[bool, typer.Option("--apply", "-a", help="apply the [pinned] conversions")] = False,
        tmp_dir: Annotated[Path, typer.Option("--working-dir", "-w",
            help="path to working dir where the processed files are stored")] = None,
        test_puid: Annotated[str, typer.Option("--test-filetype", "-tf",
            help="test a puid from the policies with a respective sample of the directory")] = None,
        test: Annotated[bool, typer.Option("--test", "-t",
            help="test all file conversions from the policies with a respective sample of the directory")] = None,
        policies_path: Annotated[Path, typer.Option("--policies-path", "-p",
            help="path to the json file with the policies")] = None,
        mode_add: Annotated[bool, typer.Option("--keep", "-k",
            help="when generating policies: it sets the keep_original flag to true (default false)."
                 "[with -c also passed: the flag in the policies is ignored and originals are not deleted]")] = False,
        strict: Annotated[bool, typer.Option("--strict", "-s",
            help="when generating policies: non default filetypes are not added as blank policies."
                 "when applying policies: moves the files that are not listed in the policies to folder FAILED.")] = False,
        blank: Annotated[bool, typer.Option("--blank", "-b",
            help="create a blank policies.json based on the files in the dir")] = False,
        mode_dry: Annotated[bool, typer.Option("--dry", "-d",
            help="dry run, not moving or converting files, just printing cmds")] = False,
        mode_cleanup: Annotated[bool, typer.Option("--cleanup", "-c",
            help="removes all temporary items and replaces the parent files with the converted ones "
                 "[with -k also passed: it just adds the converted ones]")] = False,
        mode_verbose: Annotated[bool, typer.Option("--verbose", "-v",
            help="lists every file in report, every minor error and does deeper file inspection on video files")] = False,
        save_policies: Annotated[bool, typer.Option("--save-policies", "-S",
            help="copy the local policies to conf/presets/")] = False,
        extend_policies: Annotated[bool, typer.Option("--extend-policies", "-e",
            help="append filetypes found in files_dir to the given policies if they are missing in it")] = False,
        mode_quiet: Annotated[bool, typer.Option("--quiet", "-q",
            help="just print errors and warnings")] = False
    ):

    # check path
    if not files_dir.exists():
        print(f'{files_dir} not found. exiting...')
        raise typer.Exit(1)

    # setting mode, RenderTable
    mode_inspect = False if apply else True  # apply caveat, if cmd is run with flag -a (apply the policies)
    mode = Mode(DRY=mode_dry, ADD=mode_add, STRICT=strict, VERBOSE=mode_verbose, QUIET=mode_quiet)
    rt = Rt(mode=mode)

    # configure working dir
    wdir = Path(f'{files_dir}{PathsConfig.WDIR}')
    if tmp_dir:
        if not tmp_dir.exists() and not mode.DRY:
            tmp_dir.mkdir()
        wdir = tmp_dir

    # save policies
    if save_policies:
        save_policies_from(files_dir)

    # cleanup caveat, if cmd is run with flag --cleanup
    if mode_cleanup and Path(f'{files_dir}{FileOutput.TMPSTATE}').is_file():
        clean_up(files_dir, mode_set=mode, wdir=wdir)

    # the file handler with the respective mode,
    fh = FileHandler(mode=mode)

    # scan the directory with Siegfried
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),transient=True,) as progress:
        progress.add_task(description="analysing files with siegfried...", total=None)
        sfoutput = Sf.analyse(files_dir)
    # get the json output from siegfried and parse it to SfInfo, appending the configured working dir
    sfinfos: [SfInfo] = []
    [sfinfos.append(fh.append_path_values(SFParser.to_SfInfo(metadata), files_dir, wdir)) for metadata in sfoutput]

    # the core of the app, managing the policies
    # option -p (load policies path) has the highest priority since it has to be given explicitly
    #
    # if no path given with option -p
    # case where there is already a policies file at default location, set the path:
    if not policies_path and Path(f'{files_dir}{FileOutput.POLICIES}').is_file():
        policies_path = Path(f'{files_dir}{FileOutput.POLICIES}')
    # no default policies found or the blank option is given:
    # fallback: generate the policies with optional flag blank
    if not policies_path or blank:
        if not mode_quiet:
            print("... generating policies")
        fh.gen_default_policies(files_dir, sfinfos, blank=True if blank else False)
    # load the external passed policies with option -p (polices_path)
    else:
        if not mode_quiet:
            print(f'... loading policies form {policies_path}')
        fh.load_policies(policies_path)
        fh.run_basic_analytics(sfinfos)
        # test_puid caveat, if specific puid from policies is set to be tested
        if test_puid:
            if wdir.joinpath(PathsConfig.TEST).is_dir():
                shutil.rmtree(wdir.joinpath(PathsConfig.TEST))
            fh.test_policies(sfinfos, files_dir, puid=test_puid)
            raise typer.Exit()
        # extend_policies caveat, expand a passed policies
        # with the filetypes found in files_dir that are not yet in the policies
        if extend_policies:
            if not mode_quiet:
                print(f'... updating the filetypes in policies {policies_path}')
            fh.gen_default_policies(files_dir, sfinfos, extend=policies_path.stem)
            if not mode.VERBOSE:
                raise typer.Exit()

    # apply the policies
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),transient=True,) as progress:
        progress.add_task(description="applying policies, file integrity tests ...", total=None)
        [fh.apply_policies(sfinfo=sfinfo) for sfinfo in sfinfos]

    if mode_inspect:
        if not mode_quiet:
            rt.print_diagnostic_table(fh)
        if test:
            fh.test_policies(sfinfos, files_dir)
        rt.report2file(fh=fh, path=files_dir)
        Postprocessor.dump_json(fh.pinned2protocol, files_dir, FileOutput.PROTOCOL, sha256=True)
        print("done inspecting the files.")
        raise typer.Exit()

    # start with conversion
    stack: list[SfInfo] = []
    if fh.pinned2convert:
        if not mode_quiet:
            print('... starting with file conversion. this may take a while ...')
        stack = fh.convert(fh.pinned2convert)
    else:
        Postprocessor.dump_json(fh.pinned2protocol, files_dir, FileOutput.PROTOCOL, sha256=True)
        if not mode_quiet:
            print('there was nothing to convert')
        raise typer.Exit()
    # cleanup
    pp = Postprocessor(mode=mode)
    if mode_cleanup:
        # see if there is already a protocol
        processed = parse_protocol(files_dir)
        # append any sfinfo that were pinned to protocol
        processed.extend(fh.pinned2protocol)
        stack = pp.cleanup(stack, processed, files_dir, wdir)
        # dump the protocol
        pp.dump_json(stack, files_dir, FileOutput.PROTOCOL, sha256=True)
    else:
        stack.extend(fh.pinned2protocol)
        pp.dump_json(stack, files_dir, FileOutput.TMPSTATE, sha256=True)


if __name__ == "__main__":
    typer.run(main)
