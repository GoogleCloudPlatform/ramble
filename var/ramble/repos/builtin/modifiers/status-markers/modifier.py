# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import llnl.util.filesystem as fs

from ramble.modkit import *


class StatusMarkers(BasicModifier):
    """Modifier to create a marker file when the experiment has started and
    ended.

    This modifier will create a .started and .finished file within the
    experiment run dir.
    """

    name = "status-markers"

    tags("status", "info")

    _started_marker = "status.{experiment_namespace}.started"
    _finished_marker = "status.{experiment_namespace}.finished"

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode")

    register_builtin(
        "write_started_marker", required=True, injection_method="prepend"
    )

    def write_started_marker(self):
        cmds = [
            f'echo "Started" > "{{workspace_root}}/{self._started_marker}" 2>&1',
            f'rm -f "{{workspace_root}}/{self._finished_marker}"',
        ]

        return cmds

    register_builtin(
        "write_finished_marker", required=True, injection_method="append"
    )

    def write_finished_marker(self):
        cmds = [
            f'echo "Finished" > "{{workspace_root}}/{self._finished_marker}" 2>&1'
        ]

        return cmds

    register_phase(
        "clean_markers", pipeline="setup", run_after=["make_experiments"]
    )

    def _clean_markers(self, workspace, app_inst=None):
        started_marker = self.expander.expand_var(
            f"{{workspace_root}}/{self._started_marker}"
        )
        finished_marker = self.expander.expand_var(
            f"{{workspace_root}}/{self._finished_marker}"
        )

        for marker in [started_marker, finished_marker]:
            if os.path.isfile(marker):
                fs.force_remove(marker)
