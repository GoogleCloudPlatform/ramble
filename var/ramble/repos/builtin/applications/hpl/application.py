# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.base_app.builtin.hpl import Hpl as HplBase


class Hpl(HplBase):
    """Define HPL application"""

    name = "hpl"

    maintainers("douglasjacobsen")

    version("2.3", "Version 2.3 of HPL", preferred=True)

    with when("package_manager_family=spack"):
        define_compiler("gcc9", pkg_spec="gcc@9.3.0")

        software_spec("impi_2018", pkg_spec="intel-oneapi-mpi@2021.13.1")

        software_spec(
            "hpl-{application_version}",
            pkg_spec="hpl@{application_version} +openmp",
            compiler="gcc9",
        )

        required_package("hpl")

    executable("execute", "xhpl", use_mpi=True)

    workload("standard", executables=["execute"])
    workload("calculator", executables=["execute"])

    workload_group("standard", workloads=["standard"], mode="append")
    workload_group("calculator", workloads=["calculator"], mode="append")
