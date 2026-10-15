#!/bin/bash

. {batch_helpers}

has_job_file
if [ $? == 0 ]; then
  exit 0
fi

BATCH_UID=$(get_job_uid)

gcloud logging read --project {batch_project} labels.job_uid=$BATCH_UID &> {experiment_run_dir}/batch_job_log
