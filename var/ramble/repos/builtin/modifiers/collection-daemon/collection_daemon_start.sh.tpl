#!/bin/bash

TEST_NAME="$1"
CMD="$2"
SLEEP="$3"
cd {experiment_run_dir}

COLLECTION_DIR=$(dirname {collection_daemon_log_prefix})

NODE_IDX=$(awk -v h="$(hostname)" '$0 == h { print NR; exit }' {hostfile})
NODE_IDX=$(printf "%03d" $NODE_IDX)

DAEMON_PID=$$
END_FILE=$COLLECTION_DIR/.end_collection
PID_FILE=$COLLECTION_DIR/pid-values.node-$NODE_IDX

echo "$DAEMON_PID" >> $PID_FILE

while  [ ! -f $END_FILE ]; do
  bash -c "$CMD >> {collection_daemon_log_prefix}.daemon-$TEST_NAME.node-$NODE_IDX 2>&1"
  sleep $SLEEP
done
