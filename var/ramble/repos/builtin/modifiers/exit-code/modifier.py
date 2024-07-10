# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.config
from ramble.modkit import *  # noqa: F403


class ExitCode(BasicModifier):
    """Define a modifier to capture exit codes from executables

    The exit code that is captured by this modifier is the last portion
    of every executable template.

    As a result, the exit codes tracked might not be accurate if the
    experiments being executed have many templates within singular executable
    definitions.
    """

    name = "exit-code"

    tags("info")

    maintainers("douglasjacobsen")

    mode(
        "auto", description="Auto detected shell based on config:shell setting"
    )

    default_mode("auto")

    modifier_variable(
        "exit_code_log",
        default="{experiment_run_dir}/exit_codes.out",
        description="Log file exit codes are written to",
        modes=["*"],
    )

    modifier_variable(
        "exit_code_name",
        default="{executable_name}_exit_code",
        description="Format for exit code name",
        modes=["*"],
    )

    modifier_variable(
        "bash_exit_code_variable",
        default="$?",
        description="Exit code env-var for bash and sh",
        modes=["*"],
    )

    modifier_variable(
        "csh_exit_code_variable",
        default="$status",
        description="Exit code env-var for csh",
        modes=["*"],
    )

    modifier_variable(
        "fish_exit_code_variable",
        default="$status",
        description="Exit code env-var for fish",
        modes=["*"],
    )

    modifier_variable(
        "bat_exit_code_variable",
        default="%errorlevel%",
        description="Exit code env-var for windows batch files",
        modes=["*"],
    )

    archive_pattern("{exit_code_log}")

    executable_modifier("capture_exit_codes")

    def capture_exit_codes(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_exec = []
        post_exec = []

        shell = self._usage_mode
        if shell == "auto":
            shell = ramble.config.get("config:shell")

        exit_code_str = 'echo "Exit code for {executable_name}: '

        if shell in ["bash", "sh"]:
            exit_code_str += '{bash_exit_code_variable}"'
        elif shell == "csh":
            exit_code_str += '{csh_exit_code_variable}"'
        elif shell == "fish":
            exit_code_str += '{fish_exit_code_variable}"'
        elif shell == "bat":
            exit_code_str += '{bat_exit_code_variable}"'

        post_exec.append(
            CommandExecutable(
                f"capture-exit-code-{executable_name}",
                template=[
                    exit_code_str,
                ],
                redirect="{exit_code_log}",
            )
        )

        return pre_exec, post_exec

    exit_code_regex = r"Exit code for (?P<exec_name>.*): (?P<exit_code>[0-9]+)"

    figure_of_merit_context(
        "Executable Exit Code",
        regex=exit_code_regex,
        output_format="Exit code from {exec_name}",
    )

    figure_of_merit(
        "Exit code",
        fom_regex=exit_code_regex,
        group_name="exit_code",
        units="",
        log_file="{exit_code_log}",
        contexts=["Executable Exit Code"],
    )

    register_phase(
        "examine_all_exit_codes",
        pipeline="analyze",
        run_before=["analyze_experiments"],
    )

    def _examine_all_exit_codes(self, workspace, app_inst=None):
        """Determine the max value from all exit codes"""
        import os
        import re

        log_file = get_file_path(
            app_inst.expander.expand_var("{exit_code_log}"), workspace
        )

        logger.all_msg(f" Exit code log: {log_file}")

        exit_regex = re.compile(self.exit_code_regex)
        final_regex = re.compile("Final exit code: (?P<exit_code>[0-9]+)")

        max_code = 0
        final_found = False

        if os.path.exists(log_file):
            with open(log_file) as f:
                for line in f.readlines():
                    logger.all_msg(f" Exit line: {line}")
                    m = exit_regex.match(line)

                    if m:
                        logger.all_msg(f'   Match: {m.group("exit_code")}')
                        max_code = max(max_code, int(m.group("exit_code")))

                    if final_regex.match(line):
                        final_found = True

            if not final_found:
                with open(log_file, "a") as f:
                    f.write(f"Final exit code: {max_code}")

    success_criteria(
        "Final Exit Code Zero",
        mode="string",
        match="Final exit code: 0",
        file="{exit_code_log}",
    )
