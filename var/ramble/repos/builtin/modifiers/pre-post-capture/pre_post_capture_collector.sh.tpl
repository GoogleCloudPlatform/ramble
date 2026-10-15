#!/bin/bash

ORDER="$1"
CAPTURE_NAME="$2"
CMD="$3"
cd {experiment_run_dir}
mkdir -p $(dirname {pre_post_capture_log_prefix})

NODE_IDX=`awk "/$(hostname)/{ print NR; exit }" {hostfile}`
NODE_IDX=$(printf "%03d" $NODE_IDX)

$CMD >> {pre_post_capture_log_prefix}.$ORDER-$CAPTURE_NAME.node-$NODE_IDX 2>&1
