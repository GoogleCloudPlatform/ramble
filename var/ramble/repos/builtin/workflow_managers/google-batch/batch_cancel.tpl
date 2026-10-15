#!/bin/bash

BATCH_FILE={experiment_run_dir}/.batch_job.yaml

. {batch_helpers}

has_job_file
if [ $? == 0 ]; then
  exit 0
fi

job_in_list
if [ $? == 1 ]; then
  JOB_NAME=$(get_job_name)
  
  gcloud batch jobs delete --project {batch_project} --location {batch_job_region} $JOB_NAME
fi
