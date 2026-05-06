# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.base_app.builtin.hpcg import Hpcg as BaseHpcg
from ramble.base_app.builtin.nvidia_hpc_benchmarks import (
    NvidiaHpcBenchmarks as NvidiaHpcBase,
)


class NvidiaHpcg(BaseHpcg, NvidiaHpcBase):
    """NVIDIA's HPCG benchmark accelerates the High Performance Conjugate
    Gradients (HPCG) Benchmark. HPCG is a software package that performs a
    fixed number of multigrid preconditioned (using a symmetric Gauss-Seidel
    smoother) conjugate gradient (PCG) iterations using double precision
    (64-bit) floating point values."""

    name = "nvidia-hpcg"

    maintainers("douglasjacobsen")

    executable(
        "execute",
        "{internal_mpi_command} /workspace/hpcg.sh --dat {experiment_run_dir}/hpcg.dat",
        use_mpi=True,
    )

    workload("standard", executables=["execute"])

    workload_group("all_workloads", workloads=["standard"], mode="append")
