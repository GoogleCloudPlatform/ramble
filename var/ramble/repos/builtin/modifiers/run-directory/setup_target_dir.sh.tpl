#!/bin/bash

mkdir -p {target_directory}

if [ -x "$(command -v rsync)" ]; then
    rsync -a "{source_directory}/" "{target_directory}/"
else
    cp -r "{source_directory}/." "{target_directory}"
fi
