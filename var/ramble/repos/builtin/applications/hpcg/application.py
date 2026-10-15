# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.base_app.builtin.hpcg import Hpcg as BaseHpcg


class Hpcg(BaseHpcg):
    """The High Performance Conjugate Gradients (HPCG) Benchmark project is an
    effort to create a new metric for ranking HPC systems. HPCG is intended as
    a complement to the High Performance LINPACK (HPL) benchmark, currently
    used to rank the TOP500 computing systems. The computational and data
    access patterns of HPL are still representative of some important scalable
    applications, but not all. HPCG is designed to exercise computational and
    data access patterns that more closely match a different and broad set of
    important applications, and to give incentive to computer system designers
    to invest in capabilities that will have impact on the collective
    performance of these applications."""

    name = "hpcg"

    maintainers("douglasjacobsen")

    version("3.1", "Version 3.1 of HPCG", preferred=True)

    with when("package_manager_family=spack"):
        define_compiler("gcc14", pkg_spec="gcc@14.2.0")

        software_spec(
            "intel-mpi",
            pkg_spec="intel-oneapi-mpi@2021.17.2",
        )

        software_spec(
            "hpcg-{application::hpcg::version}",
            pkg_spec="hpcg@{application::hpcg::version} +openmp",
            compiler="gcc14",
        )

        required_package("hpcg")

    workload("standard", executables=["execute", "move-log"])
    workload("calculator", executables=["execute", "move-log"])

    workload_group(
        "all_workloads", workloads=["standard", "calculator"], mode="append"
    )
    workload_group("calculator", workloads=["calculator"], mode="append")
