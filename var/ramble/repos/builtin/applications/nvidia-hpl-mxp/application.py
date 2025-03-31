# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.base_app.builtin.hpl import Hpl as HplBase
from ramble.base_app.builtin.nvidia_hpc_benchmarks import (
    NvidiaHpcBenchmarks as NvidiaHpcBase,
)


class NvidiaHplMxp(HplBase, NvidiaHpcBase):
    """This application defines how to run NVIDIA's optimized version of HPL,
    which is contained in NVIDIA's HPC-Benchmarks collection.

    The NVIDIA HPC-Benchmarks collection provides four benchmarks (HPL,
    HPL-MxP, HPCG, and STREAM) widely used in the HPC community optimized for
    performance on NVIDIA accelerated HPC systems.

    NVIDIA's HPL and HPL-MxP benchmarks provide software packages to solve a
    (random) dense linear system in double precision (64-bit) arithmetic and in
    mixed precision arithmetic using Tensor Cores, respectively, on
    distributed-memory computers equipped with NVIDIA GPUs, based on the Netlib HPL
    benchmark and HPL-MxP benchmark.

    https://catalog.ngc.nvidia.com/orgs/nvidia/containers/hpc-benchmarks
    """

    name = "nvidia-hpl-mxp"

    maintainers("douglasjacobsen")

    tags("benchmark-app", "benchmark", "linpack", "optimized", "nvidia")

    executable(
        "execute",
        '{internal_mpi_command} /workspace/hpl-mxp.sh --gpu-affinity "{gpu_affinity}" --n {Ns} --nb {block_size} --nprow {Ps} --npcol {Qs} --nporder {nporder}',
        use_mpi=True,
    )

    workload("standard", executables=["execute"])
    workload("calculator", executables=["execute"])

    workload_group("standard", workloads=["standard"], mode="append")
    workload_group("calculator", workloads=["calculator"], mode="append")
    workload_group(
        "all_workloads",
        workloads=["standard", "calculator"],
    )

    workload_variable(
        "block_size",
        default="1024",
        description="Size of each block",
        workload_group="calculator",
    )

    workload_variable(
        "nporder",
        default="row",
        description="Major order to use for matrix",
        values=["row", "column"],
        workload_group="all_workloads",
    )

    workload_variable(
        "gpu_affinity",
        default="0:1:2:3:4:5:6:7",
        description="Colon delimited list of GPU IDs",
        workload_group="all_workloads",
    )

    # MxP FOMs
    gflops_regex = (
        r"\s+GFLOPS = (?P<gflops>\S+), per GPU =\s+(?P<per_gflops>\S+)"
    )
    lu_gflops_regex = (
        r"\s+LU GFLOPS = (?P<gflops>\S+), per GPU =\s+(?P<per_gflops>\S+)"
    )
    figure_of_merit(
        "Total GFlops",
        fom_regex=gflops_regex,
        group_name="gflops",
        units="GFLOP/s",
        fom_type=FomType.THROUGHPUT,
    )
    figure_of_merit(
        "Per GPU GFlops",
        fom_regex=gflops_regex,
        group_name="per_gflops",
        units="GFLOP/s",
        fom_type=FomType.THROUGHPUT,
    )

    figure_of_merit(
        "Total LU GFlops",
        fom_regex=lu_gflops_regex,
        group_name="gflops",
        units="GFLOP/s",
        fom_type=FomType.THROUGHPUT,
    )
    figure_of_merit(
        "Per GPU LU GFlops",
        fom_regex=lu_gflops_regex,
        group_name="per_gflops",
        units="GFLOP/s",
        fom_type=FomType.THROUGHPUT,
    )
