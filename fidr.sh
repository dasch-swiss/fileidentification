#!/bin/bash

# get variables for mounting the volume in docker
input_dir=$(realpath "$1")
mnt_dir="$input_dir"

# if it is a file, mount the parent
if [[ -f $1 ]]; then
  mnt_dir="${mnt_dir%/*}"
fi

# store the params
params=("${@:2}")

# check if external policies are passed and store the path
add_volumes=()
while [ $# -gt 0 ]; do
    if [[ $1 == "-p"* ]] || [[ $1 == "-ep"* ]] || [[ $1 == "--policies-path"* ]]; then
        policies_path=$(realpath "$2")
        add_volumes+=("-v")
        add_volumes+=("$policies_path:$policies_path")
        shift
    fi
    if [[ $1 == "--tmp-dir"* ]]; then
        tmp_dir=$(realpath "$2")
        add_volumes+=("-v")
        add_volumes+=("$tmp_dir:$tmp_dir")
        shift
    fi
    shift
done

# run the command
docker run --rm -v "$mnt_dir":"$mnt_dir" "${add_volumes[@]}" -t fileidentification "$input_dir" "${params[@]}"
