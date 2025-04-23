# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.wm.builtin.slurm import Slurm as SlurmBase
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
