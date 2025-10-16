#!/bin/bash

# get variables for mounting the volume in docker
input_dir=$(realpath "$1")
parent_dir=${input_dir%/*}

# if it is a file, mount the parent from the parent
if [[ -f $1 ]]; then
  parent_dir="${parent_dir%/*}"
fi

# store the params
params=("${@:2}")

# check if external policies are passed and store the path
while [ $# -gt 0 ]; do
    if [[ $1 == "-p"* ]] || [[ $1 == "-ep"* ]] || [[ $1 == "--policies-path"* ]]; then
        policies_path=$(realpath "$2")
        shift
    fi
    shift
done

add_volumes=()
if [[ -f $policies_path ]]; then
  add_volumes+=("-v")
  add_volumes+=("$policies_path:$policies_path")
fi

docker run -v "$parent_dir":"$parent_dir" "${add_volumes[@]}" -t fileidentification "$input_dir" "${params[@]}"
