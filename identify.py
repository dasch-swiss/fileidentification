import json
import logging
import typer
from typing_extensions import Annotated
from pathlib import Path
from fileidentification.wrappers import homebrew_packeges
from fileidentification.wrappers.wrappers import sf_analyse
from fileidentification.filehandling import FileHandler

# check for the dependencies
homebrew_packeges.check()


def main(
        path: Annotated[Path, typer.Argument(help="path to the directory or file")],
        policies: Annotated[Path, typer.Option(help="path to the json file with the policies")] = "conf/policies.json",
        cleanup: Annotated[bool, typer.Option("--cleanup",
                                              help="cleans up renamed and converted files and folders directly")] = False,
        strict: Annotated[bool, typer.Option("--strict",
                                             help="moves the files that are not listed in the policies in to an "
                                                  "created folder called FAILED")] = False

        ):

    #  basic logging
    logging.basicConfig(filename=f'{path}.log', level=logging.INFO,  format='%(levelname)-8s %(message)s')

    filehandler = FileHandler()
    filehandler.load_policies(policies, Path("conf/fmt2ext.json"))
    modified, cleanup_instructions = filehandler.handle(
                                                        sfinfos=sf_analyse(path.absolute()),
                                                        root_path=path.absolute(),
                                                        cleanup=True if cleanup else False,
                                                        strict=True if strict else False
    )

    if modified:
        with open(f'{path}_protocol.json', 'w') as f:
            json.dump(modified, f, indent=4, ensure_ascii=False)
    if cleanup_instructions:
        with open(f'{path}_cleanup.json', 'w') as f:
            json.dump(cleanup_instructions, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    typer.run(main)
