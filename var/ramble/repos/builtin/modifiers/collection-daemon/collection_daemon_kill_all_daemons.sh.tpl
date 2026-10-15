#!/bin/bash
cd {experiment_run_dir}
COLLECTION_DIR=$(dirname {collection_daemon_log_prefix})

NODE_IDX=$(awk -v h="$(hostname)" '$0 == h { print NR; exit }' {hostfile})
NODE_IDX=$(printf "%03d" $NODE_IDX)

PID_FILE=$COLLECTION_DIR/pid-values.node-$NODE_IDX

for PID in `cat $PID_FILE`;
do
  if [ -d /proc/$PID ]; then
    kill -9 $PID
  fi
done

exit 0
