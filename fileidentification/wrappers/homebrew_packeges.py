import subprocess
import shutil


def cmd_exists(cmd):
    return shutil.which(cmd) is not None


def check() -> None:

    if not cmd_exists("brew"):
        print("you need homebrew installed, -> https://brew.sh/")
        quit()

    # siegfried
    if not cmd_exists("sf"):
        print("installing siegfried, this can take a while...")
        res = subprocess.run(["brew", "install", "richardlehane/digipres/siegfried"],
                             capture_output=True, text=True)
        if res.stderr:
            print(f'got an error, while installing: \n {res.stderr}')
        print(res.stdout)

    # ffmpeg
    if not cmd_exists("ffmpeg"):
        print("installing ffmpeg, this can take a while ...")
        res = subprocess.run(["brew", "install", "ffmpeg"], capture_output=True, text=True)
        if res.stderr:
            print(f'got an error, while installing: \n {res.stderr}')
        print(res.stdout)

    # imagemagick
    if not cmd_exists("convert"):
        print("installing imagemagick, this can take a while ... ")
        res = subprocess.run(["brew", "install", "imagemagick"], capture_output=True, text=True)
        if res.stderr:
            print(f'got an error, while installing: \n {res.stderr}')
        print(res.stdout)

    # libreOffice (used headless)
    if not cmd_exists("/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        print("LibreOffice is not installed. it is needed if you want to migrate doc to docx etc (or pdf)")
        print("... and its open source :) ")
        quit()

    print("siegfried, ffmpeg, imagemagick seems to be installed, ready to go...")
