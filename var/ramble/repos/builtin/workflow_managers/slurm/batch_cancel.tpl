#!/bin/bash

. {batch_helpers}

job_id=$(get_job_id)

# Use verbose to print out warnings of invalid job_id
scancel --verbose ${job_id}
