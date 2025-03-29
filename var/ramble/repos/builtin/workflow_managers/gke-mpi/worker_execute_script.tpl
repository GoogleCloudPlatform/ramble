#!/bin/bash
mkdir -p {container_work_dir} && cd {container_work_dir}
# important to resolve symlink
cp --remove-destination -r -L /config/* .
/usr/sbin/sshd -De -f /etc/ssh/sshd_config
