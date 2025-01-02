# Copyright 2022-2025 The Ramble Authors
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

    _started_marker = ".started"
    _finished_marker = ".finished"

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode")

    register_builtin(
        "write_started_marker", required=True, injection_method="prepend"
    )

    def write_started_marker(self):
        cmds = [
            'echo "Started" &> {experiment_run_dir}/' + self._started_marker,
            "rm -f {experiment_run_dir}/" + self.finished_marker,
        ]

        return cmds

    register_builtin(
        "write_finished_marker", required=True, injection_method="append"
    )

    def write_finished_marker(self):
        cmds = [
            'echo "Finished" &> {experiment_run_dir}/' + self._finished_marker
        ]

        return cmds

    register_phase(
        "clean_markers", pipeline="setup", run_after=["make_experiments"]
    )

    def _clean_markers(self, workspace, app_inst=None):
        exp_dir = self.expander.expand_var_name(
            app_inst.keywords.experiment_run_dir
        )

        started_marker = os.path.join(exp_dir, self._started_marker)
        finished_marker = os.path.join(exp_dir, self._finished_marker)

        for marker in [started_marker, finished_marker]:
            if os.path.isfile(marker):
                fs.force_remove(marker)
