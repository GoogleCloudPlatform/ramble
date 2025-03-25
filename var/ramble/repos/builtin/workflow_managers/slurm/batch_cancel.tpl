#!/bin/bash

. {batch_helpers}

job_id=$(get_job_id) || exit 0

scancel ${job_id}
