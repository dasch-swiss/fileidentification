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
```
or for Linux depending on your distribution
```
https://github.com/richardlehane/siegfried/wiki/Getting-started
apt-get install ffmpeg
https://inkscape.org/de/release/inkscape-1.2/gnulinux/ubuntu/ppa/dl/
https://imagemagick.org/script/download.php#linux
```
LibreOffice https://www.libreoffice.org/download/download-libreoffice/<br>

it's a first version, not tested a lot and for sure needs some more debugging... also, it is not optimised on speed,
especially when converting files. the idea was to write a script that has some default file conversion but is at the same
time highly customisable.<br>
<br>
the script turns the output from siegfried into a SfInfo dataclass per file, looks up the policies defined in **conf/policies.py**
and writes out a default **policies.json**. in a second iteration, it applies the policies 
(probes the file - if it is corrupt - if file format is accepted or it need to be converted).
then it converts the files flagged for conversion, verifies their output.

it writes all relevant metadata to a protocol.json containing a sequence of
SfInfo objects that got enriched with the the file (conversion) processing logs 
(so all file manipulation and format issues are logged).


### installation

```poetry install```

### usage

run it in your ide or in your terminal
activating the venv<br>
```source .venv/bin/active # this depends on your venv settings```
<br>or<br>
```poetry shell```

### generating policies
```
python3 identify.py path/to/directory
```
this does generate a default policies file according to the settings in conf/policies.py<br>
you get:<br>
**path/to/directory_policies.json**  -> the policies for that folder<br>
**path/to/directory_report.txt** -> a report about the filetypes, duplicates etc. and planned conversions<br>
as an addition, it moves corrupted files to a foler path/to/directory_FAILED

### applying the policies
if you're happy with the policies, you can apply them with<br>
```
python3 identify.py path/to/directory -a
```
you get the converted files in path/to/directory_WORKINGDIR<br>
### cleanup
if you're happy with the outcome you can replace the parent files with the converted ones running<br>
```
python3 identify.py path/to/directory -c
```
this also deletes all temporary folders and you get a<br>
**path/to/directory_protocol.json** -> listing all file modification in the diretory<br>

if you don't need these three intermediate states, you can simply run
```
python3 identify.py path/to/directory -ac
```
which does all at once
### advanced usage

you can also create your own policies file, and with that, customise the file conversion output 
(and executionsteps of the script.) simply edit the default file path/to/directory_policies.json before applying.<br>
if you want to start from scratch, you can create a blank template with all the file formats encountered
in the folder with ```python3 indentify path/to/folder -b```<br>

**policy examples:**<br>
a policy for Audio/Video Interleaved Format thats need to be transcoded to MPEG-4 Media File (Codec: AVC/H.264, Audio: AAC) looks like this
```
{
    "fmt/5": {
            "format_name": "Audio/Video Interleaved Format",  # optional
            "bin": "ffmpeg",
            "accepted": false,
            "keep_original": false,
            "target_container": "mp4",
            "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"
            "expected": [
            "fmt/199"
            ],
            "force_protocol": false
    }
}
```
a policy for Portable Network Graphics that is accepted as it is, but forced to be mentioned it in the protocol (by default only converted files are)
```
{
    "fmt/13": {
        "format_name": "Portable Network Graphics",
        "bin": "convert",
        "accepted": true
        "force_protocol": true
    },
}
```
**key** is the puid (fmt/XXX)<br>
(**format_name** optional)<br>
**accepted**: bool, false if the file needs to be converted<br>
**keep_original**: bool, whether to keep the parent of the converted file, default is false<br>
**bin**: program to convert the file or test the file (testing currently only is 
supported on image/audio/video, i.e. ffmpeg and imagemagick)<br>
accepted values are:<br><br>
"" [no program used, the file are also not tested for their integrity]<br>
convert [use imagemagick]<br>
ffmpeg [use ffmpeg]<br>
soffice [use libre office]<br>


**target_container**: the container the file needs to be converted<br>
**processing_args**: the arguments used with bin<br>
**expected** the expected file format for the converted file<br>
**force_protocol**: bool, if the files of this format are forced to be mentioned in the protocol. default false
(only the modified files are mentioned in the protocol)<br>
<br>
you can test an entire policies file (given that the path is path/to/directory_policies.json, otherwise pass 
the path to the file with -p) with
```
python3 identify.py path/to/directory -t
```
if you just want to test a specific policy, append f and the puid
```
python3 identify.py path/to/directory -tf fmt/XXX
```
the testconversions are located in path/to/directory_WORKINGDIR/_TEST
### presets
once you've done your work on a customised polices, you might want to save it as a preset 
(given the path of the policies is path/to/directory_policies.json )
```
python3 identify.py path/to/directory -S
```
you can reuse it on another folder with the flag -p:
```
python3 identify.py path/to/directory -p presets/yourSavedPoliciesName
```
if you're not sure what files to expect in that folder and you mind skipping them during processing, 
you can add the flag -e which expands the policies with blank ones that are not yet in the policies and writes a 
new file path/to/directory_policies.json which you can adjust before applying them.
```
python3 identify.py path/to/directory -ep presets/yourSavedPoliciesName
```
### default settings
the default setting for file conversion are in **conf/policies.py**, you can add or modify the entries there. all other
settings such as default path values or hash algorithm are at the top of the **conf/models.py** file

### options
**-a**<br>
[--apply] applies the policies<br><br>
**-c**<br>
[--clean-up] removes all temporary items and replaces the parent files with the converted ones.<br><br>
**-p path/to/policies.json**<br>
[--policies-path] load a custom policies<br><br>
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
**-k**<br>
[--keep] this overrides the keep_original value in the policies and sets it to true when cleaning up.<br>
when used in generating policies, it sets keep_original in the policies to true (default false)<br><br>
**-d**<br>
[--dry] dry run, prints out the cmds<br><br>
**-v**<br>
[--verbose] prints out more detailed diagnostics, lists every file in the report.txt and does deeper fileinspections on 
video files<br><br>
**-q**<br>
[--quiet] just print errors and warnings<br><br>

### iterations

as the SfInfo objects of converted files have an **derived_from** attribute that is again a SfInfo object of its parent, 
and an existing protocol is extended if a folder is run against a different policy, the protocol keeps track of all
iterations.<br>
so iterations like A -> B, B -> C, ... is logged in one protocol.<br>
<br>
e.g. if you have different types of doc and docx files in a folder, you dont allow doc and you want a pdf as an addition 
to the docx files, and a thumbnail of the first page of the pdf ... , you can save the respective presets: the first doc 
-> docx, the second docx -> pdf with "keep_original": true ...
<br>
then you can use
```
python3 chain.py path/to/directory --p presets/preset1 --p presets/preset2 ...
```
**NOTE** as it is not possible to add flags to the iteration steps, each step is executed with the flags -acq
(apply, cleanup, quiet), so if you want to keep some of the files you plan to convert in one of the steps, make sure
that you set it in the respective policies accordingly.

### remote

there is a very basic script for handling files that are remote, given you have an Siegfried dump 
```sf -json path/to/directory``` of the files, an ssh user for the server with sufficient rights (read/write for the
folder) and you did already exchange keys with ssh-copy-id.
```
python3 remote.py path/to/the/siegfrieddump.json [-p path/to/policies -user: username -ip: ip]
```
it creates a folder named after the dump and fetches all the files from the server that are flagged to convert in the 
given policies. than you can apply the policies with identify. if the converted files have to be approved by the owner 
of the remote server, you can run
```
python3 python3 remote.py path/to/the/siegfrieddump.json --send
```
which sends the files from the working dir as well as the protocol to the server. if you need to do that, make sure
to run it before cleanup (-c)

### updating signatures

siegfried<br>
```sf -update```

check https://www.nationalarchives.gov.uk/aboutapps/pronom/droid-signature-files.htm
and adapt version in ```conf/droidsig2json.py``` and run it. you should get an updated **fmt2ext.json** (its not
automated because the site is painful to parse)

you'll find a good resource for fileformats on<br>
https://www.nationalarchives.gov.uk/PRONOM/Format/proFormatSearch.aspx?status=new


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
