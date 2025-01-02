# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class SuccessCriteria(BasicModifier):
    """Define a modifier with a success criteria"""

    name = "success-criteria"

    mode("test", description="This is a test mode")

    figure_of_merit(
        "experiment status",
        fom_regex=r".*Experiment status:\s+(?P<status>[\S_]+)\s*",
        group_name="status",
        units="",
    )

    success_criteria(
        "success_criteria_status_check",
        mode="fom_comparison",
        fom_name="experiment status",
        formula="'{value}' == 'SUCCESS'",
    )

    success_criteria(
        "status",
        mode="string",
        match=".*Experiment status: SUCCESS",
        file="{log_file}",
    )

    variable_modification(
        "experiment_status",
        modification="Experiment status: SUCCESS",
        method="set",
        mode="test",
    )

    register_builtin("echo_status", required=True)

    def echo_status(self):
        return ['echo "Experiment status: {experiment_status}" >> {log_file}']
