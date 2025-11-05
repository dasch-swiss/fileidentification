#!/bin/bash

# get variables for mounting the volume in docker
input_dir=$(realpath "$1")
mnt_dir="$input_dir"

# if it is a file, mount the parent
if [[ -f $1 ]]; then
  mnt_dir="${mnt_dir%/*}"
fi

# parse the args and store potential paths for volumes to mount in docker
# set relative path to absolute
add_volumes=()
params=()
while [ $# -gt 0 ]; do
    if [[ $(realpath "$1") == $input_dir ]]; then
        shift
    fi
    if [[ $1 == "-p" ]] || [[ $1 == "-ep" ]] || [[ $1 == "--policies-path" ]]; then
        policies_path=$(realpath "$2")
        add_volumes+=("-v" "$policies_path:$policies_path")
        params+=("$1" "$policies_path")
        shift 2
    fi
    if [[ $1 == "--tmp-dir" ]]; then
        mkdir -p "$2"
        tmp_dir=$(realpath "$2")
        add_volumes+=("-v" "$tmp_dir:$tmp_dir")
        params+=("$1" "$tmp_dir")
        shift 2
    fi
    if [[ $1 != "" ]]; then
      params+=("$1")
    fi
    shift
done

# run the command
docker run --rm -v "$mnt_dir":"$mnt_dir" "${add_volumes[@]}" -t fileidentification "$input_dir" "${params[@]}"
