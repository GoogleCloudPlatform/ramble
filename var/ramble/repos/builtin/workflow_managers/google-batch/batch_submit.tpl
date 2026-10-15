#!/bin/bash
. {batch_helpers}

has_job_file
if [ $? == 1 ]; then
  JOB_NAME=$(get_job_name)

  job_in_list
  if [ $? == 1 ]; then
    echo "Previous job ${JOB_NAME} is still in batch queue. Will not resubmit."
    exit 0
  fi

  echo 'Stale job file found for experiment {experiment_namespace}. Remove with `ramble on --executor="\{batch_clean\}"`. Will not submit.'
  exit 0
fi

{batch_submit_cmd} > $BATCH_FILE 2> {experiment_run_dir}/.batch_submit_err

has_job_file
FILE_EXISTS=$?
if [ $FILE_EXISTS == 1 ]; then
  JOB_NAME=$(get_job_name)

  if [ ! -z "$JOB_NAME" ]; then
    echo "Job $JOB_NAME was submitted successfully"
  fi
  if [ -z "$JOB_NAME" ]; then
    echo "Error submitting experiment {experiment_namespace} to Google Batch."
    exit 1
  fi
fi
if [ $FILE_EXISTS == 0 ]; then
  echo "Experiment {experiment_namespace} failed to submit."
fi
