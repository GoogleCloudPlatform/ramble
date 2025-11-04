# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.wmkit import *


class UserManaged(WorkflowManagerBase):
    """Simple workflow manager that offers sensible default behavior"""

    name = "user-managed"

    workflow_manager_variable(
        "workflow_banner",
        default="""# ****************************************************
# * No workflow is used with this experiment
# * Execution command: {batch_submit}
# * If this file is not the same as the above path, it is unlikely that this script
# * is used when `ramble on` executes experiments.
# ****************************************************
""",
        description="Banner to describe the workflow within execution templates",
    )

    workflow_manager_variable(
        name="mpi_command",
        default="mpirun -n {n_ranks}",
        description="mpirun prefix, mostly served as an overridable default",
    )

    workflow_manager_variable(
        name="batch_submit",
        default="{execute_experiment}",
        description="batch_submit script, mostly served as an overridable default",
    )

    def get_status(self, workspace):
        """Return status of a given job"""
        return None
