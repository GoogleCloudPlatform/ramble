#!/bin/bash

get_job_id() {
    local job_id=$(< {experiment_run_dir}/.slurm_job)
    if [ -z "${job_id:-}" ]; then
        echo "No valid job_id found" 1>&2
        exit 1
    fi
    echo ${job_id}
}
