# Copyright 2022-2025 The Ramble Authors
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

    with when("package_manager_family=spack"):
        define_compiler("gcc9", pkg_spec="gcc@9.3.0")

        software_spec("impi2018", pkg_spec="intel-mpi@2018.4.274")

        software_spec(
            "hpcg",
            pkg_spec="hpcg@3.1 +openmp",
            compiler="gcc9",
        )

        required_package("hpcg")

    workload("standard", executables=["execute", "move-log"])

    workload_group("all_workloads", workloads=["standard"], mode="append")
