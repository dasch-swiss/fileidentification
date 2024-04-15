import json
import typer
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
from typing_extensions import Annotated
from conf.models import ServerCon, FileOutput, SfInfo
from fileidentification.filehandling import FileHandler, PreProcessor, Postprocessor, Mode
from fileidentification.parser.parser import SFParser
from fileidentification.wrappers.wrappers import Rsync


def main(
        sfdump: Annotated[Path, typer.Argument(help="path to the Siegfried json dump")],
        policies_path: Annotated[Path, typer.Option("--policies-path", "-p",
            help="path to the json file with the policies, filetype with 'accepted: false' are being"
                 "fetched from the remote server (if not flag -a)")] = None,
        user: Annotated[str, typer.Option("-user", help="user of server")] = None,
        ip: Annotated[str, typer.Option("-ip", help="ip of server")] = None,
        add: Annotated[bool, typer.Option("--all", "-a", help="fetch all files")] = False,
        send: Annotated[bool, typer.Option("--send", "-s", help="send the converted files to the server")] = False,
        mode_dry: Annotated[bool, typer.Option("--dry", "-d",
            help="dry run, not moving or converting files, just printing cmds")] = False,
    ):

    mode = Mode(DRY=mode_dry, ADD=True if add or send else False)

    # get the dump
    if not sfdump.is_file():
        print("dump not found")
        raise typer.Exit(1)

    files_dir = sfdump.with_suffix("")

    # configure working dir
    if not files_dir.exists():
        files_dir.mkdir()

    # configure server connection
    if not Path(f'{files_dir}{FileOutput.REMOTESERVER}').is_file():
        if not user:
            user = typer.prompt("the username on the server")
        if not ip:
            ip = typer.prompt("the ip of the server")
        Path(f'{files_dir}{FileOutput.REMOTESERVER}').write_text(json.dumps(asdict(ServerCon(ip, user))))

    server = json.loads(Path(f'{files_dir}{FileOutput.REMOTESERVER}').read_text())
    server = ServerCon(ip=server["ip"], user=server["user"])

    # verify ssh keys
    home_dir = Path.home()
    ssh_keys = home_dir.joinpath(f'.ssh/')
    if not ssh_keys.is_dir():
        print("you need to generate ssh keys first for this to work")
        raise typer.Exit(1)
    known_host = ssh_keys.joinpath(f'known_hosts')
    ips = known_host.read_text()
    if not server.ip in ips:
        print("please run a ssh-copy-id to the server")
        raise typer.Exit(1)

    if send:
        # look for an existing protocol
        protocol = Postprocessor.verify_file(Path(f'{files_dir}{FileOutput.PROTOCOL}'), sha256=True)
        processed: list[SfInfo] = []
        if isinstance(protocol, Path):
            print(f'... reading from {protocol}')
            processed.extend(SFParser.read_protocol(protocol))
        pp = Postprocessor(mode=mode)
        tmp_protocol = pp.verify_file(Path(f'{files_dir}{FileOutput.TMPSTATE}'), sha256=True)
        if isinstance(tmp_protocol, Path):
            stack = SFParser.read_protocol(tmp_protocol)
            stack = pp.cleanup(stack, processed, files_dir, server=server)
            # dump it as log and send it to server
            pp.dump_json(stack, files_dir, f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_log.json')
            Rsync.copy(f'{files_dir}{datetime.now().strftime("%Y%m%d_%H%M%S")}_log.json', 'log/', server=server)
            print('...did send the files...')
            raise typer.Exit()
        else:
            print(tmp_protocol)
            raise typer.Exit(1)

    with open(sfdump) as f:
        res = json.load(f)
    sfoutput = res['files']

    sfinfos: [SfInfo] = []
    [sfinfos.append(SFParser.to_SfInfo(metadata)) for metadata in sfoutput]

    fh = FileHandler(mode=mode)
    if not policies_path:
        fh.gen_default_policies(files_dir, sfinfos)
    else:
        fh.load_policies(policies_path)

    preprocessor = PreProcessor(mode=mode, policies=fh.policies)
    preprocessor.fetch_remote(sfinfos, server, files_dir)




if __name__ == "__main__":
    typer.run(main)
