import shutil
import platform


def cmd_exists(cmd):
    return shutil.which(cmd) is not None


def check() -> None:
    if platform.system() == "Darwin":
        if not cmd_exists("brew"):
            print("you need homebrew installed, -> https://brew.sh/")
            quit()

    # siegfried
    if not cmd_exists("sf"):
        if platform.system() == "Darwin":
            print("you need siegfried for this to work, please install it with running this cmd in your terminal:")
            print("brew install richardlehane/digipres/siegfried")
        if platform.system() == "Linux":
            print("you need siegfried for this to work, please install it depending on your distribution:")
            print("https://github.com/richardlehane/siegfried/wiki/Getting-started")
        quit()

    # ffmpeg
    if not cmd_exists("ffmpeg"):
        print("you need ffmpeg for this to work, please install it with running this cmd in your terminal:")
        if platform.system() == "Darwin":
            print("brew install ffmpeg")
        if platform.system() == "Linux":
            print("apt-get install ffmpeg")
        quit()

    # imagemagick
    if not cmd_exists("magick"):
        print("you need imagemagick for this to work, please install it with running this cmd in your terminal:")
        if platform.system() == "Darwin":
            print("brew install imagemagick")
            print("brew install ghostscript")
        if platform.system() == "Linux":
            print("https://imagemagick.org/script/download.php#linux")
        quit()

    # libreOffice (used headless)
    if platform.system() == "Darwin":
        if not cmd_exists("/Applications/LibreOffice.app/Contents/MacOS/soffice"):
            print("LibreOffice is not installed. it is needed if you want to migrate doc to docx etc (or pdf)")
            print("... and its open source :) ")
            quit()
    if platform.system() == "Linux":
        if not cmd_exists("libreoffice"):
            print("LibreOffice is not installed. it is needed if you want to migrate doc to docx etc (or pdf)")
            print("... and its open source :) ")
            quit()
