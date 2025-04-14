# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.wm.builtin.slurm import Slurm as SlurmBase
from ramble.wmkit import *


class SlurmPyxis(SlurmBase):
    """Pyxis support for Slurm workflow manager"""

    name = "slurm-pyxis"

    maintainers("dapomeroy")

    tags("workflow", "slurm", "pyxis")

    def __init__(self, file_path):
        super().__init__(file_path)

    workflow_manager_variable(
        name="srun_args",
        default=(
            "-n {n_ranks} --container-image {container_path} "
            + '--container-mounts \"{container_mounts}\" '  # fmt: skip
            + "--container-env {container_env_vars} --container-writable"
        ),
        description="Arguments passed to srun",
    )

    workflow_manager_variable(
        name="container_path",
        default="",
        description="Path to container image",
    )

    workflow_manager_variable(
        name="container_env_vars",
        default="",
        description="Environment variables to pass to container",
    )
