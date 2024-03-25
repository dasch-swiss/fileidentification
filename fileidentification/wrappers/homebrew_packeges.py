import shutil


def cmd_exists(cmd):
    return shutil.which(cmd) is not None


def check() -> None:

    if not cmd_exists("brew"):
        print("you need homebrew installed, -> https://brew.sh/")
        quit()

    # siegfried
    if not cmd_exists("sf"):
        print("you need siegfried for this to work, please install it with running this cmd in your terminal:")
        print("brew install richardlehane/digipres/siegfried")
        quit()

    # ffmpeg
    if not cmd_exists("ffmpeg"):
        print("you need ffmpeg for this to work, please install it with running this cmd in your terminal:")
        print("brew install ffmpeg")

    # imagemagick
    if not cmd_exists("convert"):
        print("you need imagemagick for this to work, please install it with running this cmd in your terminal:")
        print("brew install imagemagick")
        print("brew install ghostscript")
        quit()

    # libreOffice (used headless)
    if not cmd_exists("/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        print("LibreOffice is not installed. it is needed if you want to migrate doc to docx etc (or pdf)")
        print("... and its open source :) ")
        quit()

