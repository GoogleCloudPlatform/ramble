# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.wmkit import *


class WhenWorkflowManager(WorkflowManagerBase):
    name = "when-workflow-manager"

    variant(
        "workflow_manager_included",
        default=False,
        values=[True, False],
        description="Test variant",
    )

    with when("+workflow_manager_included"):
        workflow_manager_variable(
            "wm_var_test", default="included", description="Test variable"
        )

    variant(
        "workflow_manager_env_var_included",
        default=False,
        values=[True, False],
        description="Test workflow manager env vars",
    )

    with when("+workflow_manager_env_var_included"):
        environment_variable(
            "WORKFLOW_ENV_VAR",
            value="WF_ENV_VAR_SET",
            description="Test env variable",
        )

    variant(
        "wf_man_required_variable",
        default=False,
        values=[True, False],
        description="Test required variable",
    )

    required_variable(
        "test_wf_man_required_variable",
        description="Test required variable",
        when=["+wf_man_required_variable"],
    )

    variant(
        "wf_man_required_key",
        default=False,
        values=[True, False],
        description="Test required key",
    )

    required_variable(
        "test_wf_man_required_key",
        results_level="key",
        description="Test required key",
        when=["+wf_man_required_key"],
    )

    def get_status(self, workspace):
        """Return status of a given job"""
        return None
