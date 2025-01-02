# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class PreExecPrint(BasicModifier):
    """Pre Execution Print modifier

    This modifier injects an echo of '{experiment_namespace}' at the beginning
    of each experiment.

    The content of this echo can be overridden by setting the value of the
    'pre_exec_print_template' variable to a print template you would like to use.
    """

    name = "pre-exec-print"

    tags("experiment-info")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode for pre-print")
    default_mode("standard")

    executable_modifier("pre_exec_print")

    _attr_name = "_applied_pre_exec_print"

    def pre_exec_print(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_cmds = []
        post_cmds = []

        if not hasattr(self, self._attr_name):
            echo_string = "Index: {experiment_index} -- Namespace: {experiment_namespace}"
            if "pre_exec_print_template" in app_inst.variables:
                echo_string = "{pre_exec_print_template}"
            pre_cmds.append(
                CommandExecutable(
                    "perform-pre-exec-print",
                    template=[f'echo "Running: {echo_string}"'],
                    mpi=False,
                    redirect="",
                    output_capture="",
                )
            )
            setattr(self, self._attr_name, True)
        return pre_cmds, post_cmds
