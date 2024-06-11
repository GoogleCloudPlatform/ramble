# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import re

from ramble.modkit import *


class ConditionalPsm3(BasicModifier):
    """Modifier to apply PSM3 (conditionally, based on MPI)

    This modifier will conditionally apply PSM3 to all mpi commands within an
    experiment. It works by determining if the experiment uses a specific MPI
    implementation, as defined by the variable `psm3_mpi`.

    The experiment will contain commands which grep for the MPI defined by
    `psm3_mpi` in the spack environment the experiment will use. If it is
    found, environment variables (in bash/sh form) will be injected into the
    execution environment.

    These environment variables are removed after the command finishes.
    """

    name = "conditional-psm3"

    tags("mpi-provider")

    maintainers("douglasjacobsen")

    mode(
        "standard", description="Standard execution mode for conditional PSM3"
    )

    executable_modifier("apply_psm3")

    required_variable("psm3_mpi")
    required_package("intel-oneapi-mpi", package_manager="spack*")

    modifier_variable(
        "apply_psm3_exec_regex",
        default="",
        description="When the non-empty regex matches with the executable_name, apply psm3 even if mpi is not explicitly used",
        mode="standard",
    )

    modifier_variable(
        "psm3_log_file",
        default="{log_file}",
        description="Log file where PSM3 info writes to, this varies based on applications",
        mode="standard",
    )

    def apply_psm3(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_cmds = []
        post_cmds = []

        exec_regex = self.expander.expand_var_name("apply_psm3_exec_regex")
        should_apply = executable.mpi or (
            exec_regex and re.match(exec_regex, executable_name)
        )

        if should_apply:
            pre_cmds.append(
                CommandExecutable(
                    f"add-psm3-{executable_name}",
                    template=[
                        'grep "{psm3_mpi}" {env_path}/spack.yaml &> /dev/null',
                        "if [ $? -eq 0 ]; then",
                        "spack load {psm3_mpi}",
                        'export FI_PROVIDER="psm3"',
                        "export PSM3_ALLOW_ROUTERS=1",
                        'export PSM3_HAL="sockets"',
                        "export PSM3_IDENTIFY=1",
                        "fi",
                    ],
                    mpi=False,
                    redirect="",
                    output_capture="",
                )
            )

            post_cmds.append(
                CommandExecutable(
                    f"remove-psm3-{executable_name}",
                    template=[
                        'grep "{psm3_mpi}" {env_path}/spack.yaml &> /dev/null',
                        "if [ $? -eq 0 ]; then",
                        "spack unload {psm3_mpi}",
                        "unset FI_PROVIDER",
                        "unset PSM3_ALLOW_ROUTERS",
                        "unset PSM3_HAL",
                        "unset PSM3_IDENTIFY",
                        "fi",
                    ],
                    mpi=False,
                    redirect="",
                    output_capture="",
                )
            )

        return pre_cmds, post_cmds

    psm3_build_info_regex = r".*\sPSM3_IDENTIFY PSM3\s+(?P<version>v[\d.]+)\s+built for\s+(?P<target>.*)$"

    figure_of_merit(
        "PSM3 version",
        fom_regex=psm3_build_info_regex,
        group_name="version",
        units="",
        log_file="{psm3_log_file}",
    )

    figure_of_merit(
        "PSM3 build target",
        fom_regex=psm3_build_info_regex,
        group_name="target",
        units="",
        log_file="{psm3_log_file}",
    )
