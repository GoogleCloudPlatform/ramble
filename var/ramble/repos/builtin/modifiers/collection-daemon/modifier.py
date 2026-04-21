# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import shlex

from ramble.modkit import *


class CollectionDaemon(BasicModifier):
    """Define a modifier that starts (and eventually terminates) a collection daemon"""

    name = "collection-daemon"

    tags("debugging")
    maintainers("douglasjacobsen")

    mode("collection", description="Standard execution mode")
    default_mode("collection")

    modifier_variable(
        "collection_daemon_log_prefix",
        default="{experiment_run_dir}/collection_daemon/collection_daemon",
        description="Directory to store daemon output",
        modes=["*"],
    )

    modifier_variable(
        "collection_daemon_names",
        expandable=False,
        default=[],
        description="Names to apply to collections",
        mode="collection",
    )

    modifier_variable(
        "collection_daemon_commands",
        expandable=False,
        default=[],
        description="Commands to collect",
        mode="collection",
    )

    modifier_variable(
        "collection_daemon_poll_interval_in_sec",
        default="10",
        modes=["collection"],
        description="Polling interval, in seconds, to poll the collection daemon",
    )

    required_variable("hostfile")
    required_variable("hostlist")

    archive_pattern("{collection_daemon_log_prefix}.*")

    register_template(
        "collection_daemon_start",
        src_path="collection_daemon_start.sh.tpl",
        dest_path="collection_daemon_start.sh",
    )

    register_template(
        "collection_daemon_run_kill",
        src_path="collection_daemon_run_kill.sh.tpl",
        dest_path="collection_daemon_run_kill.sh",
    )

    register_template(
        "collection_daemon_kill_all_daemons",
        src_path="collection_daemon_kill_all_daemons.sh.tpl",
        dest_path="collection_daemon_kill_all_daemons.sh",
    )

    register_builtin("setup_log_dir", injection_method="prepend")
    register_builtin(
        "start_daemons",
        injection_method="prepend",
        depends_on=["setup_log_dir"],
    )
    register_builtin("kill_daemons", injection_method="append")

    def setup_log_dir(self):
        run_dir = self.expander.expand_var_name("experiment_run_dir")
        log_prefix = self.expander.expand_var_name(
            "collection_daemon_log_prefix"
        )

        assert run_dir in log_prefix

        return [
            "LOG_DIR=$(dirname {collection_daemon_log_prefix})",
            "if [ -d $LOG_DIR ]; then",
            "  rm -rf $(dirname {collection_daemon_log_prefix})",
            "fi",
            "mkdir -p $(dirname {collection_daemon_log_prefix})",
        ]

    def start_daemons(self):
        daemon_commands = self.expander.expand_var(
            "{collection_daemon_commands}", typed=True
        )
        daemon_names = self.expander.expand_var(
            "{collection_daemon_names}", typed=True
        )
        interval = self.expander.expand_var(
            "{collection_daemon_poll_interval_in_sec}"
        )
        start_cmds = [
            'trap "{collection_daemon_run_kill}" SIGINT SIGTERM',
        ]

        if not isinstance(daemon_commands, list) or not isinstance(
            daemon_names, list
        ):
            return start_cmds

        if len(daemon_commands) != len(daemon_names):
            logger.warn(
                "The collection_daemon_names and collection_daemon_commands arguments have "
                f"different lengths in experiments {self.expander.experiment_namespace}"
            )

        for name, cmd in zip(daemon_names, daemon_commands):
            arguments = f"{shlex.quote(name)} {shlex.quote(cmd)} {shlex.quote(interval)}"
            start_cmds.append(
                f'pdsh -R ssh -w {{hostlist}} "nohup {{collection_daemon_start}} {arguments}" &'
            )

        return start_cmds

    def kill_daemons(self):
        return ["{collection_daemon_run_kill}"]
