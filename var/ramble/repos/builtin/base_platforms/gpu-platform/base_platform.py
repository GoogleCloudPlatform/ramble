# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.platkit import *


class GpuPlatform(PlatformBase):
    """Platform representing a node with available GPU compute capabilities

    GPU quantities are set through the following variables:
    - n_accelerators: Global number of accelerators in an experiment
    - accelerators_per_node: Number of accelerators to user per node
    """

    name = "gpu-platform"

    variant(
        "accelerator",
        default=True,
        description="GPU Platforms should have a GPU accelerator by default",
    )

    variant(
        "accelerator_type",
        default="GPU",
        values=["GPU"],
        description="Type of accelerator on this platform",
    )
