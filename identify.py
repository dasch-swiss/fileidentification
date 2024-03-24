import sys
import json
import logging
from fileidentification.wrappers import homebrew_packeges
from fileidentification.wrappers.wrappers import sf_analyse
from fileidentification.filehandling import FileHandler

# check for the dependencies
homebrew_packeges.check()


def main():

    path = sys.argv[1]
    # logging
    logging.basicConfig(filename=f'{path}.log', level=logging.INFO,  format='%(levelname)-8s %(message)s')

    filehandler = FileHandler()
    filehandler.load_policies("conf/policies.json", "conf/fmt2ext.json")
    modified, cleanup = filehandler.handle(sf_analyse(path))

    if modified:
        with open(f'{path}_modified.json', 'w') as f:
            json.dump(modified, f, indent=4, ensure_ascii=False)
    if cleanup:
        with open(f'{path}_cleanup.json', 'w') as f:
            json.dump(cleanup, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
