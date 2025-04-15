#!/bin/bash

if [ -x "$(command -v rsync)" ]; then
    rsync --include='{retained_files_glob}' --exclude='*' "{target_directory}/" "{source_directory}/"
else
    cp -r "{target_directory}/{glob_pattern}" "{source_directory}/"
fi
