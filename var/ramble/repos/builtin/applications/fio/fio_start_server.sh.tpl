#!/bin/bash
{load_software_env}

SERVER_PID_FILE="{experiment_run_dir}/server_$(hostname).pid"
fio --server --daemonize="$SERVER_PID_FILE" &
sleep 5
PID=$(cat "$SERVER_PID_FILE" 2>/dev/null)
if ! kill -0 "$PID" 2>/dev/null; then
    echo "ERROR: Failed to start fio server (PID $PID from '$SERVER_PID_FILE')"
    exit 1
else
    echo "Fio server started on $(hostname)"
fi
