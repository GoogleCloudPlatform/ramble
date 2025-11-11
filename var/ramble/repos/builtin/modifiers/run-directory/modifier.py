# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import re

from ramble.modkit import *


class RunDirectory(BasicModifier):
    """Modifier to run executables in a specified directory."""

    name = "run-directory"

    tags("utility")

    maintainers("linsword13")

    mode("standard", description="Standard mode for the modifier.")
    default_mode("standard")

    modifier_variable(
        "target_directory",
        default="{experiment_run_dir}",
        description="Directory where the specified executables should be run from.",
        mode="standard",
    )

    modifier_variable(
        "source_directory",
        default="{experiment_run_dir}",
        description="Directory where the experiment files should be copied from.",
        mode="standard",
    )

    modifier_variable(
        "cleanup_target_directory_before_run",
        default="True",
        description="If True, the target directory will be cleaned before the run.",
        mode="standard",
    )

    modifier_variable(
        "retained_files_glob",
        default="",
        description=(
            "The file glob patterns that get copied back to the source directory after"
            "the experiment run."
        ),
        mode="standard",
    )

    modifier_variable(
        "apply_exec_regex",
        default="",
        description="Specifies the executables that the directory change should be applied to",
        mode="standard",
    )

    register_template(
        "setup_target_dir",
        src_path="setup_target_dir.sh.tpl",
        dest_path="setup_target_dir.sh",
    )

    register_template(
        "postrun_copy",
        src_path="postrun_copy.sh.tpl",
        dest_path="postrun_copy.sh",
    )

    executable_modifier("apply_run_directory_change", usage_filter="once")

    def apply_run_directory_change(
        self, executable_name, executable, app_inst
    ) -> None:
        pre_cmds = []
        post_cmds = []
        exec_regex = self.expander.expand_var_name("apply_exec_regex")
        if not exec_regex or not re.match(exec_regex, executable_name):
            return pre_cmds, post_cmds
        target_dir = self.expander.expand_var_name("target_directory")
        source_dir = self.expander.expand_var_name("source_directory")
        if target_dir == source_dir:
            return pre_cmds, post_cmds
        from ramble.util import executable

        if not getattr(self, "_target_cleaned", False):
            self._target_cleaned = True
            should_cleanup = self.expander.expand_var_name(
                "cleanup_target_directory_before_run",
                typed=True,
            )
            if should_cleanup:
                pre_cmds.append(
                    executable.CommandExecutable(
                        "cleanup-target-dir",
                        template=[f"rm -rf {target_dir}"],
                    )
                )
            pre_cmds.append(
                executable.CommandExecutable(
                    "setup-target-dir-once",
                    template=["{setup_target_dir}"],
                )
            )
        pre_cmds.append(
            executable.CommandExecutable(
                "nav-to-target-dir",
                template=f"pushd {target_dir}",
            )
        )
        post_cmds.append(
            executable.CommandExecutable(
                "nav-to-previous-dir",
                template="popd",
            )
        )
        return pre_cmds, post_cmds

    register_builtin("retain_files", injection_method="append")

    def retain_files(self):
        glob_pattern = self.expander.expand_var_name("retained_files_glob")
        if not glob_pattern:
            return []
        target_dir = self.expander.expand_var_name("target_directory")
        source_dir = self.expander.expand_var_name("source_directory")
        if target_dir == source_dir:
            return []
        return ["{postrun_copy}"]
