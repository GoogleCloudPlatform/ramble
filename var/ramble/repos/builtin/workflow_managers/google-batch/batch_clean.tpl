#!/bin/bash
. {batch_helpers}

has_job_file
if [ $? == 1 ]; then
  JOB_NAME=$(get_job_name)

  if [ ! -z "$JOB_NAME" ]; then
    job_in_list
    LIST_CHECK=$?
    if [ $LIST_CHECK == 1 ]; then
      echo "Experiment {experiment_namespace} is still in the queue for Google Batch. Skipping clean..."
    fi

    if [ $LIST_CHECK == 0 ]; then
      echo "Removing stale batch job files for experiment {experiment_namespace}"
      rm -f $BATCH_FILE

      if [ -f $BATCH_LIST_FILE ]; then
        rm -f $BATCH_LIST_FILE
      fi
    fi
  fi

  if [ -z "$JOB_NAME" ]; then
    rm -f $BATCH_FILE
    rm -f $BATCH_LIST_FILE
  fi
fi
