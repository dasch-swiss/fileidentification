# Fileidentification

A python CLI to identify file formats and bulk convert files. It is designed for digital preservation workflows
and is basically a python wrapper around several programs. It uses [pygfried](https://pypi.org/project/pygfried/)
(a CPython extension for [siegfried](https://www.itforarchivists.com/siegfried)), ffmpeg, imagemagick (optionally inkscape) and
LibreOffice, so it's recommended to have those installed. If you are not using fileidentification a lot and don't want
to install these programs, you can run the script in a docker container. There is a dockerfile ready, the current docker
image is still heavy though (1.1 G).

Most probable use case might be when you need to test and possibly convert a huge amount of files and you
don't know in advance what file types you are dealing with. It features:

- file format identification and extraction of technical metadata with pygfried, ffprobe and imagemagick
- file integrity testing with ffmpeg and imagemagick
- file conversion with ffmpeg, imagemagick and LibreOffice using a json file as a protocol
- detailed logging

## Installation

## Docker

build the image, make the bash script executable and link it, where it is included in PATH (e.g. $HOME/.lcoal/bin)

```bash
docker build -t fileidentification .
chmod +x ./fidr.sh
ln -s `pwd`/fidr.sh $HOME/.local/bin/fidr
```

### Quickstart

- **Generate policies for your files:**

    `fidr path/to/directory`

- **Review generated policies:**

    Edit `path/to/directory_policies.json` to customize conversion rules. If edited, test the outcome of the policies

    `fidr path/to/directory -t`

- **Test the integrity of the files and apply the policies:**

    `fidr path/to/directory -iar`

- **Logfile**: see `path/to/directory_log.json`

    If you wish a simpler csv output, run `fidr path/to/directory --csv` to get a csv

-> see **Options** below for more available flags

## Manual installation

### Dependencies

Install ffmpeg, imagemagick and LibreOffice if not already installed

#### MacOS (using homebrew)

```bash
brew install ffmpeg
brew install imagemagick
brew install ghostscript
brew install --cask libreoffice
```

#### Linux

Depending on your distribution:

- [ffmpeg](https://ffmpeg.org/download.html#build-linux)
- [imagemagick](https://imagemagick.org/script/download.php#linux)
- [LibreOffice](https://www.libreoffice.org/download/download-libreoffice)

On Debian/Ubuntu

```bash
sudo apt-get update
sudo apt-get install ffmpeg imagemagick ghostscript libreoffice
```

### Python Dependencies

If you don't have [uv](https://docs.astral.sh/uv/) installed, install it with

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, you can use `uv run` to run the fileidentification script.
This creates a venv and installs all necessary python dependencies:

```bash
uv run identify.py --help
```

## Single Execution Steps Explained

### Detect File Formats - Generate Conversion Policies

`uv run identify.py path/to/directory`

Generate two json files:

**path/to/directory_log.json** : The technical metadata of all the files in the folder

**path/to/directory_policies.json** : A file conversion protocol for each file format
that was encountered in the folder according to the default policies. Edit it to customize conversion rules.

### File Integrity Tests (-i)

`uv run identify.py path/to/directory -i`

Test the files for their integrity and move corrupted files to the folder in `path/to/directory_TMP/_REMOVED`.

You can also add the flag `-v` (`--verbose`) for more detailed inspection. (see **options** below)

NOTE: Currently only audio/video and image files are tested.

### Applying Policies, File Conversion (-a)

`uv run identify.py path/to/directory -a`

Apply the policies defined in `path/to/directory_policies.json` and convert files into their target file format.
The converted files are temporary stored in `path/to/directory_TMP` (default) with the log output
of the program used as log.txt next to it.

### Clean Up Temporary Files (-r)

`uv run identify.py path/to/directory -r`

Delete all temporary files and folders and move the converted files next to their parents.

### Combining Steps - Custom Policies and Working Directory

If you don't need these intermediary steps, you can run the desired steps at once by combining their flags.
Here is an example how to do verbose testing, applying a custom policy and set the location to the tmp
directory other than default (see **option** below for more information about the flags):

`uv run identify.py path/to/directory -ariv -p path/to/custom_policies.json --tmp-dir path/to/tmp-dir`

### Log

The **path/to/directory_log.json** takes track of all modifications in the target folder.  
Since with each execution of the script it checks whether such a log exists and read/appends to that file.  
Iterations of file conversions such as A -> B, B -> C, ... are logged in the same file.

If you wish a simpler csv output, you can add the flag `--csv` anytime when you run the script,
which converts the `log.json` of the actual status of the directory to a csv.

## Advanced Usage

You can also create your own policies file, and with that, customise the file conversion output.
Simply edit the generated default file `path/to/directory_policies.json` before applying.
If you want to start from scratch, run `uv run indentify.py path/to/directory -b` to create a
blank policies template with all the file formats encountered in the folder.

### Policy Specification

A policy for a file type consists of the following fields and uses its PRONOM Unique Identifier (PUID) as a key

| Field                | Type           |                                     |
|----------------------|----------------|-------------------------------------|
| **format_name**      | **str**        | optional                            |
| **bin**              | **str**        | required                            |
| **accepted**         | **bool**       | required                            |
| **target_container** | **str**        | required if field accepted is false |
| **processing_args**  | **str**        | required if field accepted is false |
| **expected**         | **list[str]**  | required if field accepted is false |
| **remove_original**  | **bool**       | optional (default is `false`)       |

- `format_name`: The name of the file format.
- `bin`: Program to convert or test the file. Literal[`""`, `"magick"`, `"ffmpeg"`, `"soffice"`].
(Testing currently only is supported on image/audio/video, i.e. ffmpeg and magick.)
- `accepted`: `false` if the file needs to be converted, `true` if it doesn't.
- `processing_args`: The arguments used with bin. Can also be an empty string if there is no need for such arguments.
- `expected`: the expected file format for the converted file as PUID
- `remove_original`: whether to keep the parent of the converted file in the directory, default is `false`

### Policy Examples

A policy for Audio/Video Interleaved Format (avi) that need to be transcoded to MPEG-4 Media File
(Codec: AVC/H.264, Audio: AAC) looks like this

```json
{
    "fmt/5": {
        "format_name": "Audio/Video Interleaved Format",
        "bin": "ffmpeg",
        "accepted": false,
        "target_container": "mp4",
        "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac",
        "expected": [
            "fmt/199"
        ],
        "remove_original": false
    }
}
```

A policy for Portable Network Graphics that is accepted as it is, but gets tested

```json
{
    "fmt/13": {
        "format_name": "Portable Network Graphics",
        "bin": "magick",
        "accepted": true
    }
}
```

**Policy Testing:**

You can test the outcome of the conversion policies (given that the path is path/to/directory_policies.json,
otherwise pass the path to the file with -p) with

`uv run identify.py path/to/directory -t`

The script takes the smallest file for each conversion policy and converts it.
The converted files are located in _TMP/_TEST.

If you just want to test a specific policy, append f and the puid

`uv run identify.py path/to/directory -tf fmt/XXX`

## Modifying Default Settings

In the .env file you can customise some default path: e.g. the paths to the default policies, set custom default
tmp dir location.

Other default params such as PDF/A export settings for LibreOffice or other strings are in 
`fileidentification/definitions/constants.py`.

## Options

`-i`
[`--integrity-tests`] tests the files for their integrity

`-v`
[`--verbose`] catches more warnings on video and image files during the integrity tests.
this can take a significantly longer based on what files you have. As an addition,
it handles some warnings as an error.

`-a`
[`--apply`] applies the policies

`-r`
[`--remove-tmp`] removes all temporary items and adds the converted files next to their parents.

`-x`
[`--remove-original`] this overwrites the remove_original value in the policies and sets it to true when removing
the tmp files. the original files are moved to the TMP/_REMOVED folder.
When used in generating policies, it sets remove_original in the policies to true (default false).

`-s`
[`--strict`] when run in strict mode, it moves the files that are not listed in policies.json to the folder _REMOVED
(instead of throwing a warning).
When used in generating policies, it does not add blank policies for formats that are not mentioned in
fileidentification/policies/default.py

`-b`
[`--blank`] creates a blank policies based on the files encountered in the given directory.

`-q`
[`--quiet`] just print errors and warnings

`--csv`
get an additional output as csv aside from the log.json

`--convert`
re-convert the files that failed during file conversion

the following options are currently not supported when running it in a docker container

`-p`
[`--policies-path`] load a custom policies json file instead of the default policies

`-e`
[`--extend-policies`] append filetypes found in the directory to the given policies if they are missing in it.

`--tmp-dir` set a custom tmp directory where converted / removed files are stored. default is path/to/directory_TMP

## Updating Signatures

```bash
uv sync --extra update_fmt && uv run update.py
```

## Useful Links

You'll find a good resource to query for fileformats on
[nationalarchives.gov.uk](https://www.nationalarchives.gov.uk/PRONOM/Format/proFormatSearch.aspx?status=new)

The Homepage of siegfried
[itforarchivists.com/siegfried/](https://www.itforarchivists.com/siegfried/)

List of File Signatures on
[wikipedia](https://en.wikipedia.org/wiki/List_of_file_signatures)

Preservation recommendations
[kost](https://kost-ceco.ch/cms/de.html)
[bundesarchiv](https://www.bar.admin.ch/dam/bar/de/dokumente/konzepte_und_weisungen/archivtaugliche_dateiformate.1.pdf.download.pdf/archivtaugliche_dateiformate.pdf)

**NOTE**
if you want to convert to pdf/A, you need LibreOffice version 7.4+

when you convert svg, you might run into errors as the default library of imagemagick is not that good.
easiest workaround is installing inkscape ( `brew install --cask inkscape` ), make sure that you reinstall imagemagick,
so its uses inkscape as default for converting svg ( `brew remove imagemagick` , `brew install imagemagick`)
