# Fileidentification

A python CLI to identify file formats and bulk convert files. It is designed for digital preservation workflows and is basically a python wrapper arround several programs. It uses siegfried, ffmpeg, imagemagick (inkscape) and LibreOffice, so you need to have those installed for this to work. It features:

- file format identification and technical metadata with Sigfried
- file integrity testing with ffmpeg and imagemagick
- file conversion with ffmpeg, imagemagick and libreoffice using a json file as a protocol
- detailed logging

## Requiered Programs

Install siegfried, ffmpeg, imagemagick (inkscape) and LibreOffice if not already installed

### mac os (using homebrew)

```bash
brew install richardlehane/digipres/siegfried
brew install ffmpeg
brew install --cask inkscape
brew install imagemagick
brew install ghostscript
brew install --cask libreoffice
```

### linux

depending on your distribution: [siegfried](https://github.com/richardlehane/siegfried/wiki/Getting-started), [ffmpeg](https://ffmpeg.org/download.html#build-linux), [inkscape](https://wiki.inkscape.org/wiki/Installing_Inkscape#Linux), [imagemagick](https://imagemagick.org/script/download.php#linux), [libreoffice](https://www.libreoffice.org/download/download-libreoffice)

Installation using ppa

siegfried

```bash
curl -sL "http://keyserver.ubuntu.com/pks/lookup?op=get&search=0x20F802FE798E6857" | gpg --dearmor | sudo tee /usr/share/keyrings/siegfried-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/siegfried-archive-keyring.gpg] https://www.itforarchivists.com/ buster main" | sudo tee -a /etc/apt/sources.list.d/siegfried.list
sudo apt-get update && sudo apt-get install siegfried
```

ffmpeg, inkscape imagemagick and libreoffice

```bash
sudo apt-get update
sudo apt-get install ffmpeg imagemagick ghostscript inkscape libreoffice
```

### Python Dependencies

If you don't have [uv](https://docs.astral.sh/uv/) installed, install it with

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, you can use `uv run` to run the fileidentification script, this creates a venv and installs all necessary python dependencies:

```bash
uv run identify.py --help
```

## Quick Start

1. **Generate policies for your files:**
`uv run identify.py /path/to/files`

2. **Review generated policies:** Edit `files_policies.json` to customize conversion rules

3. **Test files and apply the policies:**
`uv run indentify.py /path/to/files -iar`

## Single Execution Steps

### Detect File Formats - Generate Conversion Policies

`uv run identify.py path/to/directory`

The script generates two json files:

**path/to/directory_log.json** : The technical metadata of all the files in the folder

**path/to/directory_policies.json** : A file conversion protocol for each file format that was encountered in the folder according to the default policies located in `fileidentification/policies/default.py`. Edit it to customize conversion rules.

### File Integrity Tests

`uv run identify.py path/to/directory -i`

NOTE: currently only audio/video and image files are tested.

Tests the files for their integrity and moves corrupted files to the folder in `path/to/directory_WORKINGDIR/_REMOVED`.

You can also add the flag -v (--verbose) for more detailed inspection. (see **options** below)

### File Conversion

`uv run identify.py path/to/directory -a`

This applies the policies defined in `path/to/directory_policies.json` and converts files into their target file format. The converted files are temporary stored in `path/to/directory_WORKINGDIR` (default) with the log output of the program used as log.txt next to it.

### Clean Up Temporary Files

`uv run identify.py path/to/directory -r`

This deletes all temporary files and folders and moves the converted files next to their parents.

### Combining Steps - Custom Policies and Workingdir

If you don't need these intermediary steps, you can combine the flags. E.g. if you want to load a custom policy and set the location to the working directory other than default (see **option** below for the flags):

`uv run identify.py path/to/directory -ariv -p path/to/custom_policies.json -w path/to/workingdir`

which does all at once.

### Log

The **path/to/directory_log.json** takes track of all modifications and appends logs of what changed in the target folder. Since with each execution of the script it checks whether such a log exists and read/appends to that file, iterations of file conversions such as A -> B, B -> C, ... are logged in the same file.

if you wish a simpler csv output, you can add the flag **--csv** anytime when you run the script, which converts the log.json
of the actual status of the directory to a csv.

## Advanced Usage

You can also create your own policies file, and with that, customise the file conversion output. simply edit the generated default file `path/to/directory_policies.json` before applying.
if you want to start from scratch, you can create a blank template with all the file formats encountered
in the folder with `uv run indentify.py path/to/folder -b`

**policy examples:**

a policy for Audio/Video Interleaved Format (avi) thats need to be transcoded to MPEG-4 Media File (Codec: AVC/H.264, Audio: AAC) looks like this

```json
{
    "fmt/5": {
            "bin": "ffmpeg",
            "accepted": false,
            "remove_original": false,
            "target_container": "mp4",
            "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
            "expected": [
                "fmt/199"
            ]
    }
}
```

a policy for Portable Network Graphics that is accepted as it is, but gets tested

```json
{
    "fmt/13": {
        "bin": "magick",
        "accepted": true
    }
}
```

| key                                             | is the puid (fmt/XXX)                                                                                                                         |
|-------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| **format_name** (optional)                      | **str**                                                                                                                                       |
| **bin**                                         | **str**: program to convert the file or test the file (testing currently only is supported on image/audio/video, i.e. ffmpeg and imagemagick) |
| **accepted**                                    | **bool**: false if the file needs to be converted                                                                                             |
| **remove_original** (required if not accepted)  | **bool**: whether to keep the parent of the converted file in the directory, default is false                                                 |
| **target_container** (required if not accepted) | **str**: the container the file needs to be converted to                                                                                      |
| **processing_args** (required if not accepted)  | **str**: the arguments used with bin                                                                                                          |
| **expected** (required if not accepted)         | **list**: the expected file format for the converted file                                                                                     |

accepted values for **bin** are:

| **""**       | no program used  |
|--------------|------------------|
| **magick**   | use imagemagick  |
| **ffmpeg**   | use ffmpeg       |
| **soffice**  | use libre office |
| **inkscape** | use inkscape     |

you can test an entire policies file (given that the path is path/to/directory_policies.json, otherwise pass the path to the file with -p) with

`uv run identify.py path/to/directory -t`

if you just want to test a specific policy, append f and the puid

`uv run identify.py path/to/directory -tf fmt/XXX`

the test conversions are located in _WORKINGDIR/_TEST

## Modifiying Default Settings

The default setting for file conversion are in **fileindentification/policies/default.py**, you can add or modify the entries there. all other
settings such as default path values or hash algorithm are in **fileidentification/conf/settings.py**

## Options

**-i**
[--integrity-tests] tests the files for their integrity

**-v**
[--verbose] catches more warnings on video and image files during the integrity tests.
this can take a significantly longer based on what files you have. As an addition,
it handles some warnings as an error.

**-a**
[--apply] applies the policies

**-r**
[--remove-tmp] removes all temporary items and adds the converted files next to their parents.

**-x**
[--remove-original] this overwrites the remove_original value in the policies and sets it to true when removing the tmp
files. the original files are moved to the WORKINGDIR/_REMOVED folder.
when used in generating policies, it sets remove_original in the policies to true (default false)

**-p path/to/policies.json**
[--policies-path] load a custom policies json file

**-w path/to/workingdir**
[--working-dir] set a custom working directory. default is path/to/directory_WORKINGDIR

**-s**
[--strict] when run in strict mode, it moves the files that are not listed in policies.json to the folder _REMOVED (instead of throwing a warning).
When used in generating policies, it does not add blank policies for formats that are not mentioned in fileidentification/policies/default.py

**-b**
[--blank] creates a blank policies based on the files encountered in the given directory

**-e**
[--extend-policies] append filetypes found in the directory to the given policies if they are missing in it.

**-q**
[--quiet] just print errors and warnings

**--csv**
get an additional output as csv aside from the log.json

**--convert**
re-convert the files that failed during file conversion

## using it in your code

as long as you have all the dependencies installed and run python **version >=3.8**, have **typer** installed in your project, you can copy the fileidentification folder into your project folder and import the FileHandler to your code

```python
from fileidentification.filehandling import FileHandler


# this runs it with default parameters (flags -ivarq), but change the parameters to your needs
fh = FileHandler()
fh.run("path/to/directory")


# or if you just want to do integrity tests
fh = FileHandler()
fh.integrity_tests("path/to/directoy")

# log it at some point and have an additional csv
fh.write_logs("path/where/to/log", to_csv=True)

```

## Updating Signatures

```bash
uv run update.py
```

## Useful Links

You'll find a good resource to query for fileformats on [nationalarchives.gov.uk](https://www.nationalarchives.gov.uk/PRONOM/Format/proFormatSearch.aspx?status=new)

The Homepage of Siegfried
[https://www.itforarchivists.com/siegfried/]([https://www.itforarchivists.com/siegfried/)

Signatures
[https://en.wikipedia.org/wiki/List_of_file_signatures]([https://en.wikipedia.org/wiki/List_of_file_signatures)

Preservation recommondations
[kost](https://kost-ceco.ch/cms/de.html)
[bundesarchiv](https://www.bar.admin.ch/dam/bar/de/dokumente/konzepte_und_weisungen/archivtaugliche_dateiformate.1.pdf.download.pdf/archivtaugliche_dateiformate.pdf)

**NOTE**
if you want to convert to pdf/A, you need libreOffice version 7.4+

when you convert svg, you might run into errors as the default library of imagemagick is not that good. easiest workaround
is installing inkscape ( `brew install --cask inkscape` ), make sure that you reinstall imagemagick, so its uses inkscape
as default for converting svg ( `brew remove imagemagick` , `brew install imagemagick`)
