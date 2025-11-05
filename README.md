# Fileidentification

A python CLI to identify file formats and bulk convert files.
It is designed for digital preservation workflows and is basically a python wrapper around several programs.
It uses [pygfried](https://pypi.org/project/pygfried/)
(a CPython extension for [siegfried](https://www.itforarchivists.com/siegfried)),
ffmpeg, imagemagick (optionally inkscape) and LibreOffice, so it's recommended to have those installed.
If you are not using fileidentification a lot and don't want to install these programs,
you can run the script in a docker container.
There is a dockerfile ready, the current docker image is still heavy though (1.1 G).

Most probable use case might be when you need to test and possibly convert a huge amount of files
and you don't know in advance what file types you are dealing with.
It features:

- file format identification and extraction of technical metadata with pygfried, ffprobe and imagemagick
- file probing with ffmpeg and imagemagick
- file conversion with ffmpeg, imagemagick and LibreOffice using a JSON file as a protocol
- detailed logging


## Installation

### Docker-based

Build the image, make the bash script executable,
and link it to a bin directory that appears in PATH (e.g. $HOME/.local/bin):

```bash
docker build -t fileidentification .
chmod +x ./fidr.sh
ln -s `pwd`/fidr.sh $HOME/.local/bin/fidr
```

#### Quickstart for Docker-based Installation

- **Generate policies for your files:**

    `fidr path/to/directory`
    
    this creates a folder `_fileIdentification` inside the target directory with a `_log.json` and a `_policies.json`

    Optionally review and edit `_policies.json` to customize conversion rules. If edited, optionally test the outcome
    with: `fidr path/to/directory -t`

- **Test the files on errors and apply the policies:**

    `fidr path/to/directory -iar`

The first argument has to be the root folder of your files to process, otherwise combine flags / arguments as you wish.
See **Options**, **Examples** below for more available flags.

### Manual Installation on Your System

Install ffmpeg, imagemagick and LibreOffice, if not already installed:

#### MacOS (using Homebrew)

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

On Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install ffmpeg imagemagick ghostscript libreoffice
```

#### Python Dependencies

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

This generates a folder `_fileIdentification` inside the target directory with two JSON files:

**_log.json** : The technical metadata of all the files in the folder

**_policies.json** : A file conversion protocol for each file format
that was encountered in the folder according to the default policies. Edit it to customize conversion rules.

### Inspect The Files (`-i` | `--inspect`)

`uv run identify.py path/to/directory -i`

Probe the files on errors and move corrupted files to the folder in `_fileIdentification/_REMOVED`.

Optionally add the flag `-v` (`--verbose`) for more detailed inspection (see **Options** below).

NOTE: Currently only audio/video and image files are inspected.

### Convert The Files According to the Policies (`-a` | `--apply`)

`uv run identify.py path/to/directory -a`

Apply the policies defined in `_fileIdentification/_policies.json` and convert
files into their target file format.
The converted files are temporarily stored in `_fileIdentification` with the log output
of the program used as log.txt next to it.

### Clean Up Temporary Files (`-r` | `--remove-tmp`)

`uv run identify.py path/to/directory -r`

Delete all temporary files and folders and move the converted files next to their parents.

### Log

The **_log.json** takes track of all modifications in the target folder.  
Since with each execution of the script it checks whether such a log exists and read/appends to that file.  
Iterations of file conversions such as A -> B, B -> C, ... are logged in the same file.

If you wish a simpler csv output, you can add the flag `--csv` anytime when you run the script,
which maps the `_log.json` to a csv.


## Advanced Usage

You can also create your own policies, and with that, customise the file conversion output.
Simply edit the generated default file `_fileIdentification/_policies.json` before applying or pass a customised
policies files with the parameter `-p`.
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
(Codec: AVC/H.264, Audio: AAC) looks like this:

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

A policy for Portable Network Graphics that is accepted as it is:

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

You can test the outcome of the conversion policies with

`uv run identify.py path/to/directory -t`

The script takes the smallest file for each conversion policy and converts it.

If you just want to test a specific policy, append `f` and the puid:

`uv run identify.py path/to/directory -tf fmt/XXX`

### Overview table

The basic command without flags generates a table with an overview of the encountered file types.
The rows are colored according to this color code:

- White: Policy taken over from default policies
- Yellow: Blank policy template created for that filetype (you might want to edit this policy)
  or policy missing (files of that format are skipped during processing)
- Red: Files of that format are being removed when running with flag `-s`, `--strict`

Possible values of the "Policy" column:

- `ffmpeg|magick|soffice`: Files of this format are going to be converted with the indicated program
- blank: Generated a blank policy (template)
- missing: No policy for this file type


## Options

`-i` | `--inspect`  
Probe the files on errors

`-v` | `--verbose`  
Catch more warnings on video and image files during the tests.
This can take a significantly longer time based on what files you have.

`-a` | `--apply`  
Apply the policies

`-r` | `--remove-tmp`  
Remove all temporary items and add the converted files next to their parents.

`-x` | `--remove-original`  
This overwrites the `remove_original` value in the policies and sets it to true when removing the tmp files.
The original files are moved to the `_fileIdentification/_REMOVED` folder.
When used in generating policies, it sets `remove_original` in the policies to true (default false).

`-p` | `--policies-path`  
Load a custom policies JSON file instead of generating one out of the default policies.

`-e` | `--extend-policies`  
Use with `-p`:

Append filetypes found in the directory to the custom policies if they are missing in it and generate a 
new policies json.

`-s` | `--strict`  
Move the files whose format is not listed in the policies file to the folder _REMOVED
(instead of emitting a warning).
When used in generating policies, do not add blank policies for formats that are not mentioned in DEFAULTPOLICIES.

`-b` | `--blank`  
Create a blank policies based on the file types encountered in the given directory.

`-q` | `--quiet`  
Just print errors and warnings

`--csv`  
Get output as CSV, in addition to the log.json

`--convert`  
Re-convert the files that failed during file conversion

`--tmp-dir` 
Use a custom tmp directory instead of the default `_fileIdentification`

### Examples

Use case: you have defined a set of rules in an external policies file and want to remove files of any format that
is not listed in the external policies

`fidr path/to/directory -asr -p path/to/external_policies.json`

- load an external policies JSON
- apply the policies (in strict mode, i.e. remove the files whose file type is not listed in the policies)
- remove temporary files

Use case: your files are on a external storage drive and you want to 

`fidr path/to/directory --tmp-dir path/to/tmp_dir -ivarx`

- use a custom tmp_dir to write files to (instead of the default `path/to/directory/_fileIdentification`)
- probe the files in verbose mode and apply the policies
- remove temporary files and the parents of the converted files

## Updating the PUIDs

Update the file format names and extensions of the PUIDs according to <https://www.nationalarchives.gov.uk/>.

```bash
uv sync --extra update_fmt && uv run update.py
```

creates an updated version of `fileidentification/definitions/fmt2ext.json`.
If you use the Docker-based version, don't forget to rebuild the Docker image after updating the PUIDs.

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
