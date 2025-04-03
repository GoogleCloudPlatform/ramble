# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import re

import ramble.util.shell_utils
from ramble.modkit import *
from ramble.util.executable import CommandExecutable


class SysStat(BasicModifier):
    """Define a modifier for capturing system metrics.

    Example usage: Below is a ramble config that outputs iostat every 5s
    for the duration of the sleep application.
    ```
    ramble:
      variants:
        package_manager: spack
      variables:
        apply_sampler_exe_regex: 'sleep'
        sampler_cmd: 'iostat -xzt 5'
        processes_per_node: 1
        n_nodes: 1
        mpi_command: ''
        batch_submit: '{execute_experiment}'
    applications:
      sleep:
        workloads:
          sleep:
            experiments:
              test1:
                variables:
                  sleep_seconds: 6
    software:
      packages:
        sysstat:
          pkg_spec: sysstat
      environments:
        hostname:
          packages:
          - sysstat
    modifiers:
    - name: sys-stat
    ```
    """

    name = "sys-stat"

    tags("system-info", "performance-analysis")

    mode(
        "custom",
        description="Use user-defined collection command during program run",
    )
    default_mode("custom")

    # sysstat contains common tools such as mpstat and iostat
    with when("package_manager_family=spack"):
        software_spec(
            "sysstat",
            pkg_spec="sysstat",
        )

        required_package("sysstat")

    archive_pattern("{experiment_run_dir}/sampler_*")

    modifier_variable(
        "apply_sampler_exe_regex",
        default="",
        description="Apply the sampler when exe_name matches with the regex",
        mode="custom",
    )

    modifier_variable(
        "sampler_cmd",
        default="mpstat 10",
        description="Apply the sampler when exec_name matches with the regex",
        mode="custom",
    )

    executable_modifier("apply_sampler")

    def apply_sampler(self, exe_name, exe, app_inst=None):
        pre_cmds = []
        post_cmds = []

        exe_regex = self.expander.expand_var_name("apply_sampler_exe_regex")
        applicable = exe_regex and re.match(exe_regex, exe_name)

        if applicable:
            shell = ramble.config.get("config:shell")
            last_pid_str = ramble.util.shell_utils.last_pid_var(shell)
            hostname_str = ramble.util.shell_utils.cmd_sub_str(
                shell, "uname -n"
            )

            pre_cmds.append(
                CommandExecutable(
                    f"add-sampler-{exe_name}",
                    template=[
                        f'log_path="{{experiment_run_dir}}/sampler_{exe_name}_{hostname_str}.out"',
                        '{sampler_cmd} > "$log_path" 2>&1 &',
                        f"sampler_cmd_pid={last_pid_str}",
                    ],
                    mpi=False,
                    redirect="",
                    output_capture="",
                ),
            )

            post_cmds.append(
                CommandExecutable(
                    f"cleanup-sampler-{exe_name}",
                    template=[
                        r"""
if ps -p "$sampler_cmd_pid" > /dev/null; then
    kill "$sampler_cmd_pid"
fi
            """.strip(),
                    ],
                    mpi=False,
                    redirect="",
                    output_capture="",
                )
            )

        return pre_cmds, post_cmds
