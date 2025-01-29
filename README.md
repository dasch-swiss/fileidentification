### a script to identify file formats and convert them if necessary

**disclaimer**: it has a lot of dependencies, i.e. siegfried to identify the files and
ffmpeg, imagemagick and LibreOffice if you want to test and convert files.
But they are useful anyway so you can install them for
Mac OS X using brew (optionally install inkscape, but before imagemagick):

```
brew install richardlehane/digipres/siegfried
brew install ffmpeg
brew install --cask inkscape
brew install imagemagick
brew install ghostscript
brew install --cask libreoffice
```

or for Linux depending on your distribution

```
https://github.com/richardlehane/siegfried/wiki/Getting-started
apt-get install ffmpeg
https://inkscape.org/de/release/inkscape-1.2/gnulinux/ubuntu/ppa/dl/
https://imagemagick.org/script/download.php#linux
```
LibreOffice https://www.libreoffice.org/download/download-libreoffice/<br>

it's not tested a lot and for sure needs some more debugging... also, it is not optimised on speed,
especially when converting files. the idea was to write a script that has some default file conversion but is at the same
time highly customisable.<br>
<br>
the script turns the output from siegfried into a SfInfo dataclass per file, looks up the policies defined in **conf/policies.py**
and writes out a default **policies.json**. in a second iteration, it applies the policies 
probes the file - if it is corrupt - if file format is accepted or it need to be converted).
then it converts the files flagged for conversion, verifies their output.

it writes all relevant metadata to a log.json containing a sequence of
SfInfo objects that got enriched with the the file (conversion) processing logs 
(so all file manipulation and format issues are logged).


### installation

If you don't have [uv](https://docs.astral.sh/uv/) installed, install it with

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, you can use `uv run` to run the fileidentification script:

```bash
uv run identify.py testdata   
```

By prepending `uv run` before `identify.py`,
`uv` executes the script in a virtual environment that contains all necessary python dependencies.
(The virtual environment can optionally be activated with `source .venv/bin/activate`,
but this is not necessary when using `uv run`.)

## Usage

in your terminal, switch to the root directory of fileidentification and run the script with  
`uv run identify.py` or activate the virtual environment and run `python3 identify.py`<br>

### generating policies

```
uv run identify.py path/to/directory
```

this does generate a default policies file according to the settings in conf/policies.py<br>
you get:<br>
**path/to/directory_policies.json**  -> the policies for that folder<br>
**path/to/directory_log.json** -> the technical metadata of all the files in the folder<br>

### file integrity tests

```
uv run identify.py path/to/directory -i
```

tests the files for their integrity and moves corrupted files to a folder path/to/directory_REMOVED. the affected
SfInfos in the log.json are flagged with removed<br><br>
you can also add the flag -v (--verbose) for more detailed inspection. see **options** below

### applying the policies

if you're happy with the policies, you can apply them with<br>

```
uv run identify.py path/to/directory -a
```

you get the converted files in path/to/directory_WORKINGDIR (default) with the log.txt next to it. <br><br>
You can set the path of the workingdir either
with the option -w path/to/workingdir (see **options** below) or change it permanent in **conf/settings.py**<br>

### remove temp

if you're happy with the outcome you can run<br>

```
uv run identify.py path/to/directory -r
```

this deletes all temporary folders and moves the converted file next to their parents. <br><br>
if you don't want to keep the parents of the converted files, you can add the flag -d (--delete-original). 
this replaces the parent files with the converted ones. see **options** below.<br><br>
if you don't need these intermediate states, you can simply run

```
uv run identify.py path/to/directory -iar
```

which does all at once.

### advanced usage

you can also create your own policies file, and with that, customise the file conversion output 
(and executionsteps of the script.) simply edit the default file path/to/directory_policies.json before applying.<br>
if you want to start from scratch, you can create a blank template with all the file formats encountered
in the folder with ```python3 indentify.py path/to/folder -b```<br>

**policy examples:**<br>
a policy for Audio/Video Interleaved Format thats need to be transcoded to MPEG-4 Media File (Codec: AVC/H.264, Audio: AAC) looks like this

```
{
    "fmt/5": {
            "format_name": "Audio/Video Interleaved Format",  # optional
            "bin": "ffmpeg",
            "accepted": false,
            "delete_original": true,
            "target_container": "mp4",
            "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"
            "expected": [
            "fmt/199"
            ],
    }
}
```

a policy for Portable Network Graphics that is accepted as it is

```
{
    "fmt/13": {
        "format_name": "Portable Network Graphics",
        "bin": "magick",
        "accepted": true
    }
}
```

<br><br>

| key                                             | is the puid (fmt/XXX)                                                                                                                         |
|-------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| **format_name** (optional)                      | **str**                                                                                                                                       |
| **bin**                                         | **str**: program to convert the file or test the file (testing currently only is supported on image/audio/video, i.e. ffmpeg and imagemagick) |
| **accepted**                                    | **bool**: false if the file needs to be converted                                                                                             |
| **delete_original** (required if not accepted)  | **bool**: whether to keep the parent of the converted file, default is false                                                                  |
| **target_container** (required if not accepted) | **str**: the container the file needs to be converted                                                                                         |
| **processing_args** (required if not accepted)  | **str**: the arguments used with bin                                                                                                          |
| **expected** (required if not accepted)         | **list**: the expected file format for the converted file                                                                                     |

<br><br>accepted values for **bin** are:<br>

|**""** | no program used, the file are also not tested for their integrity |
| - | - |
|**magick** | use imagemagick |
|**ffmpeg** | use ffmpeg |
|**soffice** | use libre office |
|**inkscape** | use inkscape |

<br><br>you can test an entire policies file (given that the path is path/to/directory_policies.json, otherwise pass 
the path to the file with -p) with

```
uv run identify.py path/to/directory -t
```

if you just want to test a specific policy, append f and the puid

```
uv run identify.py path/to/directory -tf fmt/XXX
```

the test conversions are located in WORKINGDIR/_TEST

### presets

once you've done your work on a customised polices, you might want to save it as a preset 
(given the path of the policies is path/to/directory_policies.json )

```
uv run identify.py path/to/directory -S
```

you can reuse it on another folder with the flag -p:

```
uv run identify.py path/to/directory -p presets/yourSavedPoliciesName
```

if you're not sure what files to expect in that folder and you mind skipping them during processing, 
you can add the flag -e which expands the policies with blank ones that are not yet in the policies and writes a 
new file path/to/directory_policies.json which you can adjust before applying them.

```
uv run identify.py path/to/directory -ep presets/yourSavedPoliciesName
```

### default settings

the default setting for file conversion are in **conf/policies.py**, you can add or modify the entries there. all other
settings such as default path values or hash algorithm are in **conf/settings.py**

### options
**-i**<br>
[--integrity-tests] tests the files for their integrity<br><br>
**-v**<br>
[--verbose] catches more warnings on video and image files during the integrity tests.
this can take a significantly longer based on what files you have. As an addition,
it handles some warnings as an error. e.g. it moves images that have an incomplete data stream into the _FAILED folder<br><br>
**-a**<br>
[--apply] applies the policies<br><br>
**-r**<br>
[--remove-tmp] removes all temporary items and adds the converted files next to their parents.<br><br>
**-p path/to/policies.json**<br>
[--policies-path] load a custom policies json file<br><br>
**-w path/to/workingdir**<br>
[--working-dir] set a custom working directory. default is path/to/directory_WORKINGDIR<br><br>
**-s**<br>
[--strict] 
when run in strict mode, it moves the files that are not listed in policies.json to a folder named _FAILED located
at the directory root of the files to analyse (instead of throwing a warning)<br>
when used in generating policies, it does not add blank ones for formats that are not mentioned in conf/policies.py<br><br>
**-b**<br>
[--blank] creates a blank policies based on the files encountered in the given directory<br><br>
**-e**<br>
[--extend-policies] append filetypes found in the directory to the given policies if they are missing in it.<br><br>
**-d**<br>
[--delete-original] this overwrites the delete_original value in the policies and sets it to true when cleaning up. so
the original files are deleted.<br>
when used in generating policies, it sets delete_original in the policies to true (default false)<br><br>
**-q**<br>
[--quiet] just print errors and warnings<br><br>

### iterations

as the SfInfo objects of converted files have an **derived_from** attribute that is again a SfInfo object of its parent, 
and an existing log.json is extended if a folder is run against a different policy, the log.json keeps track of all
iterations.<br>
so iterations like A -> B, B -> C, ... is logged in one log.json.<br>
<br>
e.g. if you have different types of doc and docx files in a folder, you dont allow doc (delete them) 
and you want a pdf as an addition to the docx files.



### updating signatures

siegfried<br>

```sf -update```

check https://www.nationalarchives.gov.uk/aboutapps/pronom/droid-signature-files.htm
and adapt version in ```conf/droidsig2json.py``` and run it. you should get an updated **fmt2ext.json** (its not
automated because the site is painful to parse)

### useful links

you'll find a good resource for query fileformats on<br>
https://www.nationalarchives.gov.uk/PRONOM/Format/proFormatSearch.aspx?status=new
<br><br>
siegfried<br>
https://www.itforarchivists.com/siegfried/
<br><br>
signatures<br>
https://en.wikipedia.org/wiki/List_of_file_signatures
<br><br>
recommendations on what file format to archive data<br>
kost: https://kost-ceco.ch/cms/de.html
<br>bundesarchiv:  https://www.bar.admin.ch/dam/bar/de/dokumente/konzepte_und_weisungen/archivtaugliche_dateiformate.1.pdf.download.pdf/archivtaugliche_dateiformate.pdf


### TODO

**config/conceptual:**\
decide on what file format to keep and to convert<br>
office files such as doc, ppt, xls are converted with LibreOffice, this means it might affect layout 

if you want to convert to pdf/A, you need libreOffice version 7.4+
it is implemented in wrappers.wrappers.Converter and conf.models.LibreOfficePdfSettings

**NOTE** when you convert svg, you might run into errors as the default library of imagemagick is not that good. easiest workaround
is installing inkscape ( ```brew install --cask inkscape``` ), make sure that you reinstall imagemagick, so its uses inkscape
as default for converting svg ( ```brew remove imagemagick``` , ```brew install imagemagick```)

**coding:**\
mostly marked in code. bigger issue are handling metadata such as exif etc. no preservation is currently implemented
when files are converted, i.e. that information gets lost

**outlook**
maybe it would be nice to make a python django app out of this, use a database (less files get written and read),
and refactor it so a taskmanager can send tasks to workers.
and there would be also a simple GUI...
