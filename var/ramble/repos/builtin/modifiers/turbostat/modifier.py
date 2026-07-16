# Copyright 2022-2026 The Ramble Authors
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


class Turbostat(BasicModifier):
    """Define a modifier for capturing CPU frequency details via turbostat.

    It runs turbostat in summary mode in the background during experiment execution.
    """

    name = "turbostat"

    tags("system-info", "performance-analysis", "cpu-frequency")

    mode("standard", description="Capture turbostat metrics in summary mode")
    default_mode("standard")

    variant(
        "use_sudo",
        default=True,
        values=[True, False],
        description="Use 'sudo' when executing turbostat commands",
    )

    variable_modification(
        "turbostat_log",
        "{experiment_run_dir}/turbostat.out",
        method="set",
        modes=["standard"],
    )

    modifier_variable(
        "sudo_prefix",
        default="sudo ",
        description="Prefix for running commands with sudo",
        modes=["standard"],
        when=["+use_sudo"],
    )

    modifier_variable(
        "sudo_prefix",
        default="",
        description="Prefix for running commands with sudo",
        modes=["standard"],
        when=["~use_sudo"],
    )

    modifier_variable(
        "turbostat_path",
        default="turbostat",
        description="Path to the turbostat executable",
        modes=["standard"],
    )

    modifier_variable(
        "turbostat_interval",
        default="1",
        description="Measurement interval in seconds for turbostat",
        modes=["standard"],
    )

    modifier_variable(
        "apply_turbostat_exe_regex",
        default=".*",
        description="Regex to match executables where turbostat should be applied",
        modes=["standard"],
    )

    archive_pattern("{turbostat_log}")

    register_builtin(
        "cleanup_turbostat", required=True, injection_method="prepend"
    )

    executable_modifier("apply_turbostat")

    def cleanup_turbostat(self):
        return [
            'rm -f "{turbostat_log}"',
        ]

    def apply_turbostat(self, exe_name, exe, app_inst=None):
        pre_cmds = []
        post_cmds = []

        exe_regex = self.expander.expand_var_name("apply_turbostat_exe_regex")
        applicable = exe_regex and re.match(exe_regex, exe_name)

        if applicable:
            shell = ramble.config.get("config:shell")
            last_pid_str = ramble.util.shell_utils.last_pid_var(shell)

            # Check if interval is set
            interval = self.expander.expand_var_name("turbostat_interval")
            interval_arg = f"-i {interval}" if interval else ""

            # Start turbostat in summary mode in the background
            pre_cmds.append(
                CommandExecutable(
                    f"start-turbostat-{exe_name}",
                    template=[
                        f'echo "turbostat results for executable: {exe_name}" >> "{{turbostat_log}}"',
                        f'{{sudo_prefix}}{{turbostat_path}} -S {interval_arg} >> "{{turbostat_log}}" 2>&1 &',
                        f"turbostat_pid={last_pid_str}",
                    ],
                    mpi=False,
                    redirect="",
                    output_capture="",
                ),
            )

            # Kill turbostat daemon after the experiment executable completes
            post_cmds.append(
                CommandExecutable(
                    f"stop-turbostat-{exe_name}",
                    template=[
                        r"""
if ps -p "$turbostat_pid" > /dev/null; then
    child_pid=$(pgrep -P "$turbostat_pid")
    if [ ! -z "$child_pid" ]; then
        {sudo_prefix}kill -INT "$child_pid" 2>/dev/null
    fi
    {sudo_prefix}kill -INT "$turbostat_pid" 2>/dev/null
fi
{sudo_prefix}pkill -INT -f "{turbostat_path} -S" 2>/dev/null
                        """.strip(),
                    ],
                    mpi=False,
                    redirect="",
                    output_capture="",
                )
            )

        return pre_cmds, post_cmds

    # Figures of merit to parse from the turbostat summary logs
    summary_regex = (
        r"^\s*(?P<avg_mhz>[0-9]+)\s+(?P<busy_pct>[0-9\.]+)\s+"
        + r"(?P<bzy_mhz>[0-9]+)\s+(?P<tsc_mhz>[0-9]+)"
    )

    figure_of_merit_context(
        "turbostat_executable",
        regex=r"turbostat results for executable:\s*(?P<exe_name>\S+)",
        output_format="turbostat on {exe_name}",
        log_file="{turbostat_log}",
    )

    figure_of_merit(
        "Avg MHz",
        log_file="{turbostat_log}",
        fom_regex=summary_regex,
        group_name="avg_mhz",
        units="MHz",
        fom_type=FomType.INFO,
        contexts=["turbostat_executable"],
    )

    figure_of_merit(
        "Busy%",
        log_file="{turbostat_log}",
        fom_regex=summary_regex,
        group_name="busy_pct",
        units="%",
        fom_type=FomType.INFO,
        contexts=["turbostat_executable"],
    )

    figure_of_merit(
        "Busy MHz",
        log_file="{turbostat_log}",
        fom_regex=summary_regex,
        group_name="bzy_mhz",
        units="MHz",
        fom_type=FomType.INFO,
        contexts=["turbostat_executable"],
    )

    figure_of_merit(
        "TSC MHz",
        log_file="{turbostat_log}",
        fom_regex=summary_regex,
        group_name="tsc_mhz",
        units="MHz",
        fom_type=FomType.INFO,
        contexts=["turbostat_executable"],
    )
