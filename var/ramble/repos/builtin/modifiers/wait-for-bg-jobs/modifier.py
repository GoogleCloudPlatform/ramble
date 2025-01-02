# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *
from ramble.util.executable import CommandExecutable
from ramble.util.shell_utils import last_pid_var


class WaitForBgJobs(BasicModifier):
    """Define a modifier for waiting for background jobs.

    This only waits for background jobs started from the experiment.
    For now, this modifier works with bash only.
    """

    name = "wait-for-bg-jobs"

    tags("info")

    mode("standard", description="Wait for background jobs using PIDs")

    default_mode("standard")

    target_shells("bash")

    register_builtin("setup_pid_array")

    def setup_pid_array(self):
        return ["wait_for_pid_list=()"]

    executable_modifier("store_bg_pid")

    def store_bg_pid(self, executable_name, executable, app_inst=None):
        post_exec = []

        if executable.run_in_background:
            shell = ramble.config.get("config:shell")
            last_pid_str = last_pid_var(shell)
            post_exec.append(
                CommandExecutable(
                    f"store-bg-pid-{executable_name}",
                    template=[f"wait_for_pid_list+=({last_pid_str})"],
                )
            )

        return [], post_exec

    register_builtin("wait_for_completion", injection_method="append")

    def wait_for_completion(self):
        return [
            'for wait_pid in "${wait_for_pid_list[@]}"; do',
            "    wait ${wait_pid}",
            "done",
        ]
