### a script to identify file formats and convert them if necessary

**disclaimer**: it has a lot of dependencies, i.e. siegfried, ffmpeg, imagemagick and LibreOffice needs to be installed.
But they are useful anyway so you can install them using brew:
```
brew install richardlehane/digipres/siegfried
brew install ffmpeg
brew install imagemagick
brew install ghostscript
```
for LibreOffice just fetch the dmg.<br>

it's a first version, not tested a lot and for sure needs some more debugging... also, it is not optimised on speed, so please be patient.

it does not delete or modify files directly, it adds converted/modified files in a folder named after that file. so your original files are untouched.

the script loops over the json returned by siegfried and then does some file conversion according to the policies defined
in **conf/policies.json**

if the file is archived as it is, it skips.

if the file has a extension missmatch, it renames a copy of it in a new folder named after the file:\
**filename.wrongExt<br>
filename/filename.ext**

the same applies to converted files, including processing logs:\
**filename.ext<br>
filename/filename.ext<br>
filename/filename.ext.log**

if an error occurs whitin integrity checks, it appends the error log to the basic log file


### installation

```poetry install```

### usage

run it in your ide or in your terminal
activating the venv<br>
```source .venv/bin/active # this depends on your venv settings```
<br>or<br>
```poetry shell```
```
python3 identify.py path/to/directory
```

you get three files:<br>
**path/to/directory.log**  -> basic logging<br>
**path/to/directory_protocol.json** -> a json with the siegfried output of files that got processed and processing logs<br>
**path/to/directory_cleanup.json** -> a json with cleanup instructions

### cleanup

after checking the converted files, you can run<br>
```
python3 cleanup.py path/to/directory_cleanup.json
```

**NOTE** this affects your original files, as they are replaced.

files that were renamed or converted are replaced by those, additional folder and conversion logs are deleted,
if the conversion was successful.

you can automate this step by setting the flag --cleanup. see advanced usage.


### advanced usage

in default use is very broad the scripts loads the policy in **conf/policies.json**.<br>
but you can also create your own policy, and with that, customise the output and executionsteps of the script.

some examples:<br>
a policy for avi thats need to be transcoded to MPEG-4 Media File (Codec: AVC/H.264, Audio: AAC) looks like this
```
{
    "fmt/5": {
            "bin": "ffmpeg",
            "accepted": false,
            "target_container": "mp4",
            "processing_args": "-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac"
    }
}
```
a policy for JPEG File Interchange Format - 1.0 that is accepted as it is
```
{
    "fmt/42": {
            "bin": "",
            "accepted": true
    }
}
```
**key** is the puid (fmt/XXX)<br>
**accepted**: bool, false if the file needs to be converted<br>
**bin**: program to convert the file or test the file (testing currently only is supported on audio/video streams, i.e. ffmpeg)<br>
**target_container**: the container the file needs to be converted<br>
**processing_args**: the arguments used with bin

there is a kind of template in conf/policies.py where you can comment out or add certain filetypes 
and generate a policies.json to your need.

**OPTIONS**<br>
**load the custom policy**<br>
```python3 identify.py /path/to/directory --policies /path/to/policies.json```

**strict mode**<br>
```python3 identify.py /path/to/directory --strict```<br>
when run in strict mode, it moves the files that are not listed in policies.json to a folder named FAILED instead of throwing a warning

**cleanup**<br>
```python3 identify.py /path/to/directory --cleanup```<br>
when setting the flag cleanup, the scipt cleans up created folders and logs and replaces the original files 
with the converted ones. you don't need to run ```python3 cleanup.py /path/to/directory_cleanup.json``` but you don't have
the intermediate state of having the original files and the converted ones side a side.


### updating signatures

siegfried<br>
```sf -update```

check [nationalarchives.gov.uk/aboutapps/pronom/droid-signature-files.htm](nationalarchives.gov.uk/aboutapps/pronom/droid-signature-files.htm)
and adapt version in ```conf/droidsig2json.py``` and run it. you should get an updated **fmt2ext.json**

you'll find a good resource for fileformats on<br>
[nationalarchives.gov.uk/PRONOM/Format/proFormatSearch.aspx?status=new](nationalarchives.gov.uk/PRONOM/Format/proFormatSearch.aspx?status=new)


### TODO

**config/conceptual:**\
decide on what file format to keep and to convert<br>
office files such as doc, ppt, xls are converted with LibreOffice, this means it might affect layout 
(or fuctions in xls)

**coding:**\
mostly marked in code. bigger issue are handling metadata such as exif etc. no preservation is currently implemented
when files are converted, i.e. that information gets lost.
