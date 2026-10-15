#!/bin/bash

STATUS_FILE={experiment_run_dir}/ramble_status.json
BATCH_FILE={experiment_run_dir}/.batch_job.yaml
BATCH_LIST_FILE={experiment_run_dir}/.batch_job_list
{declare_status_map}

job_in_list() {
  local JOB_NAME=$(get_job_name)

  local JOB_LIST=
  if [ ! -z "$JOB_NAME" ]; then
    gcloud batch jobs list --project {batch_project} --location {batch_job_region} > $BATCH_LIST_FILE 2> /dev/null
  fi

  if [ -f $BATCH_LIST_FILE ]; then
    cat $BATCH_LIST_FILE | grep "$JOB_NAME" &> /dev/null
    local LIST_CHECK=$?
    if [ $LIST_CHECK == 0 ]; then
      return 1
    fi
  fi

  return 0
}

has_job_file() {
  if [ -f $BATCH_FILE ]; then
    return 1
  fi
  return 0
}

get_job_name() {
  local BATCH_NAME=""
  if [ -f $BATCH_FILE ]; then
    local BATCH_NAME=`grep "^name:" $BATCH_FILE | awk '{print $2}'`
  fi
  echo $BATCH_NAME
}

get_job_uid() {
  local BATCH_UID=""
  if [ -f $BATCH_FILE ]; then
    local BATCH_UID=`grep "uid: " $BATCH_FILE | awk '{print $2}'`
  fi
  echo $BATCH_UID
}

update_job_description() {
  local JOB_NAME=
  if [ -f $BATCH_FILE ]; then
    local JOB_NAME=`grep "name: " $BATCH_FILE | head -n 1 | awk '{print $2}'`
  fi

  if [ ! -z "$JOB_NAME" ]; then
    gcloud batch jobs describe --project {batch_project} --location {batch_job_region} $JOB_NAME &> $BATCH_FILE
  fi
}

get_job_status() {
  local l_status
  local l_status="UNQUEUED"

  if [ -f $STATUS_FILE ]; then
    local l_status=`grep "experient_status" $STATUS_FILE | awk '{print $2}' | sed 's|"||g'`
  fi

  job_in_list
  local l_list_check=$?
  if [ $l_list_check == 0 ]; then
    local l_status="UNQUEUED"
  fi

  if [ $l_list_check == 1 -a -f $BATCH_FILE ]; then
    update_job_description

    local l_status=`grep " state: " $BATCH_FILE | head -n 1 | awk '{print $2}'` &> /dev/null
    if [ -z "$l_status" ]; then
      l_status="UNRESOLVED"
    fi

    if [ ! -z "$l_status" ]; then
      if [ -v status_map["$l_status"] ]; then
        local l_status=${status_map["$l_status"]}
      fi
    fi
  fi

  echo $l_status
}

is_job_complete() {
  local JOB_STATUS=$(get_job_status)

  if [ "$JOB_STATUS" == "UNQUEUED" ]; then
      return 1
  fi
  if [ "$JOB_STATUS" == "COMPLETE" ]; then
      return 1
  fi
  if [ "$JOB_STATUS" == "FAILED" ]; then
      return 1
  fi
  if [ "$JOB_STATUS" == "UNRESOLVED" ]; then
      return 1
  fi
  return 0
}
