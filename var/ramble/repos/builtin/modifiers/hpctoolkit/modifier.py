# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


class Hpctoolkit(BasicModifier):
    """Define a modifier for HPSF's HPC Toolkit"""

    name = "hpctoolkit"

    tags("profiler", "performance-analysis")

    maintainers("douglasjacobsen")

    mode(
        "dynamic", description="Execution mode for dynamically linked binaries"
    )
    default_mode("dynamic")

    modifier_variable(
        "hpcrun_flags",
        default="",
        description="Flags for the execution of hpcrun",
        modes=["dynamic"],
    )

    modifier_variable(
        "hpcstruct_flags",
        default="",
        description="Flags for the execution of hpcstruct",
        modes=["dynamic"],
    )

    modifier_variable(
        "hpcprof_exec",
        default="hpcprof",
        values=["hpcprof", "hpcprof-mpi"],
        description="Executable name for hpcprof",
        modes=["dynamic"],
    )

    modifier_variable(
        "hpcprof_flags",
        default="",
        description="Flags for the execution of hpcprof",
        modes=["dynamic"],
    )

    variable_modification(
        "mpi_command",
        "hpcrun {hpcrun_flags} ",
        method="append",
        modes=["dynamic"],
    )

    with when("package_manager_family=spack"):
        software_spec(
            "hpctoolkit",
            pkg_spec="hpctoolkit",
        )

        required_package("hpctoolkit")

    executable_modifier("build_hpctoolkit_commands")

    def build_hpctoolkit_commands(
        self, executable_name, executable, app_inst=None
    ):
        from ramble.util.executable import CommandExecutable

        pre_cmd = []
        post_cmd = []

        if not getattr(self, "_setup_command_base", False):
            self._setup_command_base = True
            self._hpctoolkit_databases = set()
            self._env_setup = (
                app_inst.package_manager.environment_load_commands()
            )

        if executable.mpi:
            hpctoolkit_database = (
                "{experiment_run_dir}/hpctoolkit-" + executable_name
            )
            self._hpctoolkit_databases.add(hpctoolkit_database)

            pre_cmd.append(
                CommandExecutable(
                    f"{executable_name}-hpcrun",
                    template=["export HPCRUN_OUT_PATH=" + hpctoolkit_database],
                    redirect="",
                    output_capture="",
                )
            )

        return pre_cmd, post_cmd

    register_template(
        "run_hpcstruct",
        src_path="hpctoolkit_hpcstruct.sh.tpl",
        dest_path="hpctoolkit_hpcstruct.sh",
        extra_vars_func="hpcstruct_cmd",
    )

    def _hpcstruct_cmd(self):
        cmd_str = "\n".join(self._env_setup) + "\n"
        for db in self._hpctoolkit_databases:
            cmd_str += (
                f"hpcstruct {{hpcstruct_flags}} {db} &> {db}-hpcstruct.out\n"
            )
        return {"hpctoolkit_run_hpcstruct": cmd_str}

    register_template(
        "run_hpcprof",
        src_path="hpctoolkit_hpcprof.sh.tpl",
        dest_path="hpctoolkit_hpcprof.sh",
        extra_vars_func="hpcprof_cmd",
    )

    def _hpcprof_cmd(self):
        cmd_str = "\n".join(self._env_setup) + "\n"
        for db in self._hpctoolkit_databases:
            cmd_str += f"{{hpcprof_exec}} {{hpcprof_flags}} {db} &> {db}-hpcprof.out\n"
        return {"hpctoolkit_run_hpcprof": cmd_str}
