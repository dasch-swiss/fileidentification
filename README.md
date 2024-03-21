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
in **fileidentification/conf/policies.py**

if the file is archived as it is, it skips.

if the file has a extension missmatch, it renames a copy of it in a new folder named after the file:\
**filename.wrongExt<br>
filename/filename.ext**

the same applies to converted files, including processing logs:\
**filename.ext<br>
filename/filename.ext<br>
filename/filename.ext.log**

if an error occurs whitin integrity checks, it appends the error log:\
**corrupted.ext<br>
corrupted.ext.error.log**


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
**path/to/directory_modified.json** -> a json with the siegfried output of the original files that where processed<br>
**path/to/directory_cleanup.json** -> a json with cleanup instructions

### cleanup

after checking the converted files, you can run<br>
```
python3 cleanup.py path/to/directory_cleanup.json
```
files that were renamed or converted are replaced by those, additional folder and conversion logs are deleted,
if the conversion was successful.

you can automate this step by setting the flag **cleanup=True** in the **filehandler.run()** method.


### updating signatures

siegfried<br>
```sf -update```

check [nationalarchives.gov.uk/aboutapps/pronom/droid-signature-files.htm](nationalarchives.gov.uk/aboutapps/pronom/droid-signature-files.htm)
and adapt version in ```fileidentification/conf/droidsig2json.py``` and run it. you should get an updated **fmt2ext.json**

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
