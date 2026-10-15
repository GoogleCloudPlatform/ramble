# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.appkit import *
from ramble.base_app.builtin.hpcg import Hpcg as HpcgBase
from ramble.base_app.builtin.intel_mkl_benchmarks import (
    IntelMklBenchmarks as IntelMklBenchmarksBase,
)


class IntelHpcg(HpcgBase, IntelMklBenchmarksBase):
    """Define HPCG application using Intel MKL optimized binary from intel-oneapi-mkl package"""

    name = "intel-hpcg"

    maintainers("dapomeroy")

    tags("intel-optimized")

    with when("package_manager_family=spack"):
        define_compiler("gcc14", pkg_spec="gcc@14.2.0")
        software_spec(
            "imkl_{application::intel-hpcg::version}",
            pkg_spec="intel-oneapi-mkl@{application::intel-hpcg::version} threads=openmp",
            compiler="gcc14",
        )
        software_spec(
            "impi2021p17",
            pkg_spec="intel-oneapi-mpi@2021.17.2",
        )

        required_package("intel-oneapi-mkl")

    executable(
        "set_vars", "source {intel-oneapi-mkl_path}/setvars.sh", use_mpi=False
    )  # required to link libiomp5.so
    executable("execute", "{hpcg_exec_path}", use_mpi=True)
    executable(
        "move-log", "mv n[0-9]*-[0-9]*p-[0-9]*t*.txt {out_file}", use_mpi=False
    )
    edit_file(
        "reformat-summary",
        file_path="{out_file}",
        match=" Final Summary ::",
        replace="Final Summary::",
    )
    edit_file(
        "reformat-rating",
        file_path="{out_file}",
        match="    HPCG 2.4 Rating",
        replace="HPCG 2.4 Rating",
    )

    workload(
        "standard",
        executables=[
            "set_vars",
            "execute",
            "move-log",
            "reformat-summary",
            "reformat-rating",
        ],
    )

    workload(
        "calculator",
        executables=[
            "set_vars",
            "execute",
            "move-log",
            "reformat-summary",
            "reformat-rating",
        ],
    )

    workload_group(
        "all_workloads", workloads=["standard", "calculator"], mode="append"
    )
    workload_group("calculator", workloads=["calculator"], mode="append")

    workload_variable(
        "exec_name",
        default="xhpcg_avx512",
        values=[
            "xhpcg_avx2",
            "xhpcg_avx2_int64",
            "xhpcg_avx512",
            "xhpcg_avx512_int64",
            "xhpcg_skx",
            "xhpcg_skx_int64",
            "xhpcg_sse42",
            "xhpcg_sse42_int64",
        ],
        description="Name of executable to use for Intel HPCG",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpcg_exec_path",
        default=os.path.join(
            "{mkl_benchmark_path}", "hpcg", "hpcg_cpu", "bin", "{exec_name}"
        ),
        description="Path to HPCG executable",
        workload_group="all_workloads",
    )
