#!/bin/bash
touch $(dirname {collection_daemon_log_prefix})/.end_collection
pdsh -R ssh -w {hostlist} "{collection_daemon_kill_all_daemons}"
exit 0
