#!/bin/bash

. {batch_helpers}

has_job_file
if [ $? == 0 ]; then
  exit 0
fi

BATCH_NAME=$(get_job_name)

BATCH_STATUS=$(get_job_status)

echo "Experiment {experiment_namespace} with id $BATCH_NAME has status: $BATCH_STATUS"
