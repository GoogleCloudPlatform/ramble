#!/bin/bash
mkdir -p {container_work_dir} && cd {container_work_dir}
# important to resolve symlink
cp --remove-destination -r -L /config/* .

{unformatted_command_without_logs}
