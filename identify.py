import sys
import json
import logging
from typing import Any
from fileidentification.wrappers import homebrew_packeges
from fileidentification.wrappers.wrappers import sf_analyse
from fileidentification.filehandling import check_against_policies
from fileidentification.conf.policies import accepted, conversions

# check for the dependencies
homebrew_packeges.check()


def main():

    path = sys.argv[1]
    # logging
    logging.basicConfig(filename=f'{path}.log', level=logging.INFO,  format='%(levelname)-8s %(message)s')

    # fmt2ext dict for mapping extension mismatch
    with open('fileidentification/conf/fmt2ext.json', 'r') as f:
        fmt2ext = json.load(f)

    # list to store fileinfo of modified files
    modified: list[dict[str, Any]] = []
    # analyse the files with siegfried
    res = sf_analyse(path)
    for obj in res:
        obj = check_against_policies(obj, fmt2ext, accepted, conversions)
        if obj:
            modified.append(obj)

    with open(f'{path}_modified.json', 'w') as f:
        json.dump(modified, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
