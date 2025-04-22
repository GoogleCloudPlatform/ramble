#!/bin/bash

# This is a test script that should end up in a rendered location

if [ ! -f file_list ]; then
  exit 1
fi

for FILE in `cat file_list`
do
  wc -l $FILE
done
