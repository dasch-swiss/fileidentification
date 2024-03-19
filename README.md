### a script to identify file formats and convert them if necessary

**disclaimer**: it has a lot of dependencies, i.e. siegfried, ffmpeg, imagemagick and LibreOffice needs to be installed.
Except LibreOffice, it installs those packages if needed on the first time running the script.
it's a first version, not tested a lot and for sure needs some more debugging... also, it is not optimised on speed, so please be patient.

it does not delete or modify files directly, it adds converted/modified files in a folder named after that file. so your original files are untouched.

the script loops over the json returned by siegfried and then does some file conversion according to the policies defined
in **fileidentification/conf/policies.py**

if the file is archived as it is, it skips.

if the file has a extension missmatch, it renames a copy of it in a new folder named after the file:\
**filename.wrongExt\
filename/filename.ext**

the same applies to converted files, including processing logs:\
**filename.ext\
filename/filename.ext\
filename/filename.ext.log**

if an error occurs whitin integrity checks, it appends the error log:\
**corrupted.ext\
corrupted.ext.error.log**


### installation

```poetry install```

### usage

run it in your ide or in terminal

```
poetry shell
python3 identify.py path/to/directory
```

you get two files:\
**path/to/directory.log**  -> basic logging\
**path/to/directory_modified.json** -> a json with the siegfried output of the original files that where processed
