#!/bin/bash

. {batch_helpers}

job_id=$(get_job_id) || exit 0

# Set up the status_map mapping between
# sacct/squeue status to ramble counterpart
{declare_status_map}

status=$(squeue -h -o "%t" -j "${job_id}" 2>/dev/null)
if [ -z "$status" ]; then
    status=$(sacct -j "${job_id}" -o state -X -n | xargs)
fi
if [ ! -z "$status" ]; then
    if [ -v status_map["$status"] ]; then
        status=${status_map["$status"]}
    fi
fi

saved="{experiment_run_dir}/.slurm_job_info"

echo "job {job_name} with id ${job_id} has status: $status" | tee $saved

# Print out various info about the job
echo "job info:" | tee -a $saved
echo "  job_id: ${job_id}" | tee -a $saved
echo "  job_name: {job_name}" | tee -a $saved
echo "  job_status: $status" | tee -a $saved

paste -d ":" \
  <(echo "job_nodes job_start job_end" | xargs -n1) \
  <(sacct -j "${job_id}" -o 'nodelist%80,start,end' -X -n | xargs -n1) \
  | sed "s/^/  /" \
  | tee -a $saved
