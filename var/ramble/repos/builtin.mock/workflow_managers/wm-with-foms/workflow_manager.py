# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.wmkit import *


class WmWithFoms(WorkflowManagerBase):
    """A workflow manager for testing FOMs"""

    name = "wm-with-foms"

    tags("workflow", "test")

    _fom_file = "{experiment_run_dir}/.wm_job_info"

    def _prepare_analysis(self, workspace):
        del workspace
        expander = self.app_inst.expander
        path = expander.expand_var(self._fom_file)
        with open(path, "w+") as f:
            f.write("job_status: RUNNING")

    figure_of_merit(
        "job-status",
        fom_regex=r"\s*job_status:\s*(?P<val>.*)",
        group_name="val",
        log_file="{experiment_run_dir}/.wm_job_info",
        fom_type=FomType.INFO,
    )

    def get_status(self, workspace):
        """Return status of a given job"""
        return
