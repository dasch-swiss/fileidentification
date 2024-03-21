import json
import os
import shutil
import sys


def main():

    path = sys.argv[1]

    with open(path, 'r') as f:
        tasks = json.load(f)

    for task in tasks:
        for k in task.keys():
            match k:
                case 'mv':
                    shutil.move(task[k][0], task[k][1])
                case 'rm':
                    os.remove(task[k][0])
                    shutil.rmtree(task[k][1])


if __name__ == "__main__":
    main()
