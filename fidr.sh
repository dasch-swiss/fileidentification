#!/bin/bash

# get variables for mounting the volume in docker
input_dir=$1
parent_dir=${input_dir%/*}
dir_name=${input_dir##*/}

# run the command with arguments starting at $2
docker run --rm -v $parent_dir:/data fileidentification /data/$dir_name ${@:2}
