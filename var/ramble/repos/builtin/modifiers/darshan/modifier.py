# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.modkit import *
from ramble.util import executable


class Darshan(BasicModifier):
    """Define a modifier for applying Darshan on MPI apps."""

    name = "darshan"

    tags("profiler", "io-characterization")

    maintainers("linsword13")

    mode("mpi", description="Mode for applying on MPI apps")
    default_mode("mpi")

    modifier_variable(
        "darshan_log_path",
        default="{experiment_run_dir}/darshan_logs",
        description="Path to store darshan logs",
        mode="mpi",
    )

    modifier_variable(
        "darshan_summary_cmd",
        # darshan-job-summary.pl generates a summary pdf, which is nicer to get an overview.
        # However that has a bunch of dependencies (texlive, perl modules, etc) that are not
        # properly accounted for in spack's darshan-util package. So as a default, use the
        # text-generated parser.
        default="darshan-parser",
        description="Command to generate Darshan report",
        mode="mpi",
    )

    archive_pattern("{darshan_log_path}/*")

    with when("package_manager_family=spack"):
        software_spec(
            "darshan-runtime",
            pkg_spec="darshan-runtime@3.4.6 +mpi",
        )
        software_spec(
            "darshan-util",
            pkg_spec="darshan-util@3.4.6",
        )

        required_package("darshan-runtime")
        required_package("darshan-util")

    variable_modification(
        "mpi_command",
        # This variable is filled in as part of the exec modifier below
        "${_EXTRA_DARSHAN_MOD_MPI_COMMAND}",
        method="append",
        mode="mpi",
    )

    executable_modifier("instrument_darshan")

    def instrument_darshan(self, exec_name, exec, app_inst):
        # Only support instrumenting MPI apps for now
        if not exec.mpi or self._usage_mode != "mpi":
            return [], []
        if not getattr(self, "_setup_done", False):
            self._setup_done = True
            pre_cmds = [
                "rm -rf {darshan_log_path}",
                "mkdir -p {darshan_log_path}",
            ]
        else:
            pre_cmds = []
        # Set it here instead of via env_var_modification,
        # as this needs to override the value Spack sets
        pre_cmds.append('export DARSHAN_LOG_DIR_PATH="{darshan_log_path}"')
        post_cmds = ["unset DARSHAN_LOG_DIR_PATH"]
        darshan_path = os.path.join(
            self.expander.expand_var_name("darshan-runtime_path"),
            "lib",
            "libdarshan.so",
        )
        if (
            self.expander.expand_var_name("intel-oneapi-mpi_path")
            != "{intel-oneapi-mpi_path}"
        ):
            env_flag = "-genv"
        elif self.expander.expand_var_name("openmpi_path") != "{openmpi_path}":
            env_flag = "-x"
        else:
            env_flag = ""
        if env_flag:
            pre_cmds.append(
                f'_EXTRA_DARSHAN_MOD_MPI_COMMAND="{env_flag} LD_PRELOAD {darshan_path}"'
            )
            post_cmds.append("unset _EXTRA_DARSHAN_MOD_MPI_COMMAND")
        post_cmds.append("{darshan_summary_cmd} {darshan_log_path}/*")
        pre_exec = [
            executable.CommandExecutable(
                f"set-darshan-vars-{exec_name}",
                template=pre_cmds,
            )
        ]
        post_exec = [
            executable.CommandExecutable(
                f"unset-darshan-vars-{exec_name}",
                template=post_cmds,
            )
        ]
        return pre_exec, post_exec
