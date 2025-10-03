#!/bin/bash

# get variables for mounting the volume in docker
input_dir=$(realpath "$1")
parent_dir=${input_dir%/*}
dir_name=${input_dir##*/}

# if it is a file, mount the parent from the parent
if [[ -f $1 ]]; then
  dir_name="${parent_dir##*/}/$dir_name"
  parent_dir="${parent_dir%/*}"
fi

# run the command with arguments starting at $2
docker run --rm -v "$parent_dir":/data -t fileidentification "/data/$dir_name" ${@:2}
