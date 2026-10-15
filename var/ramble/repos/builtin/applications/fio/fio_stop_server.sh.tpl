#!/bin/bash
SERVER_PID_FILE="{experiment_run_dir}/server_$(hostname).pid"

kill -9 $(cat $SERVER_PID_FILE)
sleep 5
rm -f $SERVER_PID_FILE
echo "Fio server stopped on $(hostname)"
