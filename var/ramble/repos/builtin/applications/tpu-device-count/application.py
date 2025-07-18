# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class TpuDeviceCount(ExecutableApplication):
    """This is an example application that runs on TPUs"""

    name = "tpu-device-count"

    tags("tpu")

    software_spec(
        "libtpu",
        pkg_spec="-f https://storage.googleapis.com/jax-releases/libtpu_releases.html",
        when="package_manager_family=pip",
    )

    software_spec(
        "jax",
        pkg_spec="jax[tpu]",
        when="package_manager_family=pip",
    )

    required_package("jax", when="package_manager_family=pip")

    executable(
        "count_devices",
        "python -c 'import jax; print(\"TPU cores:\", jax.device_count())'",
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    workload("count_devices", executable="count_devices")

    figure_of_merit(
        "TPU Cores",
        fom_regex=r"TPU cores: (?P<cores>[0-9]+)\s*",
        group_name="cores",
        units="",
    )

    success_criteria(
        "TPU_cores_found",
        mode="fom_comparison",
        fom_name="TPU Cores",
        formula="{value} > 0",
    )
