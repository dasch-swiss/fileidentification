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
    sfinfos = sf_analyse(path)
    modified = filehandler.run(sfinfos)

    with open(f'{path}_modified.json', 'w') as f:
        json.dump(modified, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
