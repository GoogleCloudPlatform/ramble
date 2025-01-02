# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

from ramble.base_app.builtin.hpl import Hpl as HplBase


class IntelHpl(HplBase):
    """Define HPL application using Intel MKL optimized binary from intel-oneapi-mpi package"""

    name = "intel-hpl"

    maintainers("rfbgo")

    tags("benchmark-app", "benchmark", "linpack", "optimized", "intel", "mkl")

    define_compiler("gcc13p2", pkg_spec="gcc@13.2.0", package_manager="spack*")
    software_spec(
        "imkl_2024p2",
        pkg_spec="intel-oneapi-mkl@2024.2.0 threads=openmp",
        compiler="gcc13p2",
        package_manager="spack*",
    )
    software_spec(
        "impi2021p11",
        pkg_spec="intel-oneapi-mpi@2021.11.0",
        package_manager="spack*",
    )

    required_package("intel-oneapi-mkl", package_manager="spack*")

    # This step does a few things:
    # - Prepare calling for the script runme_intel64_prv
    #   (We call this runner script instead of the underlying xhpl_intel64_dynamic
    #    since it sets up derived env var HPL_HOST_NODE for numa placement control.)
    # - Link in the xhpl_intel64_dynamic binary to the running dir
    #   (This is needed due to runme_intel64_prv invoking it using "./")
    # - Account for newer directory layout from mkl 2024
    executable(
        "prepare",
        template=[
            r"""
hpl_bench_dir="{intel-oneapi-mkl_path}/mkl/latest/benchmarks/mp_linpack"
if [ ! -d ${hpl_bench_dir} ]; then
    hpl_bench_dir="{intel-oneapi-mkl_path}/mkl/latest/share/mkl/benchmarks/mp_linpack"
fi
ln -sf ${hpl_bench_dir}/xhpl_intel64_dynamic {experiment_run_dir}/.
hpl_run="${hpl_bench_dir}/runme_intel64_prv"
    """.strip()
        ],
        mpi=False,
        redirect="",
        output_capture="",
    )

    executable(
        "execute",
        "${hpl_run}",
        use_mpi=True,
    )

    workload("standard", executables=["prepare", "execute"])
    workload("calculator", executables=["prepare", "execute"])

    workload_group("standard", workloads=["standard"], mode="append")
    workload_group("calculator", workloads=["calculator"], mode="append")

    environment_variable(
        "MPI_PROC_NUM",
        value="{n_ranks}",
        description="Number of total ranks",
        workloads=["*"],
    )

    environment_variable(
        "MPI_PER_NODE",
        value="{processes_per_node}",
        description="Number of ranks per node",
        workloads=["*"],
    )

    environment_variable(
        "NUMA_PER_MPI",
        value="{numa_per_mpi}",
        description="Number of NUMA nodes per rank",
        workloads=["*"],
    )

    environment_variable(
        "HPL_EXE",
        value="xhpl_intel64_dynamic",
        description="HPL executable name",
        workloads=["*"],
    )

    workload_variable(
        "numa_per_mpi",
        description="numa per mpi process",
        default="1",
        workloads=["*"],
    )

    # Redefine default bcast to 6 for the MKL-optimized case
    workload_variable(
        "bcast",
        default="6",
        description="BCAST for Intel MKL optimized calculator",
        workload_group="calculator",
    )
