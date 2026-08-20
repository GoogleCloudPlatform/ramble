# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.appkit import *


class IntelMklBenchmarks(ExecutableApplication):
    """The Intel MKL Benchmarks collection provides two benchmarks (HPL and
    HPCG), widely used in the HPC community optimized for performance on Intel
    hardware.
    """

    name = "intel-mkl-benchmarks"

    maintainers("dapomeroy")

    tags("cpu-benchmark", "gpu-benchmark", "intel-optimized")

    version(
        "2026.0.0",
        "Version 2026.0.0 of intel-oneapi-mkl",
    )
    version(
        "2025.3.1",
        "Version 2025.3.1 of intel-oneapi-mkl",
    )
    version(
        "2025.3.0",
        "Version 2025.3.0 of intel-oneapi-mkl",
    )
    version(
        "2025.2.0",
        "Version 2025.2.0 of intel-oneapi-mkl",
    )
    version(
        "2025.1.1",
        "Version 2025.1.1 of intel-oneapi-mkl",
    )
    version(
        "2025.0.0",
        "Version 2025.0.0 of intel-oneapi-mkl",
    )
    version(
        "2024.2.2",
        "Version 2024.2.2 of intel-oneapi-mkl",
    )
    version(
        "2024.2.1",
        "Version 2024.2.1 of intel-oneapi-mkl",
    )
    version(
        "2024.2.0",
        "Version 2024.2.0 of intel-oneapi-mkl",
        preferred=True,
    )
    version(
        "2023.2.0",
        "Version 2023.2.0 of intel-oneapi-mkl",
    )

    variable(
        "mkl_benchmark_path",
        default=os.path.join(
            "{intel-oneapi-mkl_path}",
            "mkl",
            "latest",
            "share",
            "mkl",
            "benchmarks",
        ),
        description="Path to MKL benchmarks",
        when="application_version@2024:",
    )

    variable(
        "mkl_benchmark_path",
        default=os.path.join(
            "{intel-oneapi-mkl_path}", "mkl", "latest", "benchmarks"
        ),
        description="Path to MKL benchmarks (version < 2024)",
        when="application_version@:2023",
    )
