# Copyright 2022-2025 The Ramble Authors
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

    tags("benchmark-app", "benchmark", "linpack")

    define_compiler("gcc9", pkg_spec="gcc@9.3.0", package_manager="spack*")

    software_spec(
        "impi_2018", pkg_spec="intel-mpi@2018.4.274", package_manager="spack*"
    )

    software_spec(
        "hpl",
        pkg_spec="hpl@2.3 +openmp",
        compiler="gcc9",
        package_manager="spack*",
    )

    required_package("hpl", package_manager="spack*")

    executable("execute", "xhpl", use_mpi=True)

    workload("standard", executables=["execute"])
    workload("calculator", executables=["execute"])

    workload_group("standard", workloads=["standard"], mode="append")
    workload_group("calculator", workloads=["calculator"], mode="append")
