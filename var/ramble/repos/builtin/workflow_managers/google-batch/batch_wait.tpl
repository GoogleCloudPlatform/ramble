#!/bin/bash

. {batch_helpers}

has_job_file
if [ $? == 0 ]; then
  exit 0
fi

JOB_NAME=$(get_job_name)

echo "Waiting for experiment {experiment_namespace} with id ${JOB_NAME} to complete..."

is_job_complete
END_LOOP=$?
while [ $END_LOOP == 0 ]; do
  sleep 10
  is_job_complete
  END_LOOP=$?
done
