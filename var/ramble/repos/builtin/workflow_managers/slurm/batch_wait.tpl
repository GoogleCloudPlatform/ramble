#!/bin/bash

. {batch_helpers}

job_id=$(get_job_id) || exit 0

echo "Waiting for job {job_name} with id ${job_id} to complete..."

while true; do
    status=$(squeue -h -o "%t" -j "${job_id}" 2>/dev/null)
    # The absence of the job from squeue indicates it's completed.
    if [ -z "$status" ]; then
        break
    else
        sleep 10
    fi
done

echo "job {job_name} with id ${job_id} is done"
