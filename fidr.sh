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

# run it with or without policies_path
if [[ -f $policies_path ]]; then
  docker run --rm -v "$parent_dir":"$parent_dir" -v "$policies_path":"$policies_path" -t fileidentification "$input_dir" "${params[@]}"
else
  docker run --rm -v "$parent_dir":"$parent_dir" -t fileidentification "$input_dir" "${params[@]}"
fi
