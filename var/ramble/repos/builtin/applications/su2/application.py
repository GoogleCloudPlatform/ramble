# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.appkit import *


class Su2(ExecutableApplication):
    """Define SU2 (Stanford University Unstructured) application.

    See https://su2code.github.io/ for more details.
    """

    name = "su2"

    tags("cfd", "fluid-dynamics", "multi-physics")

    maintainers("linsword13")

    with when("package_manager_family=spack"):
        define_compiler("gcc12", pkg_spec="gcc@12.2.0")
        # See https://github.com/spack/spack/pull/50601 for building with intel mpi.
        software_spec("impi2021p13", pkg_spec="intel-oneapi-mpi@13.1.0")
        software_spec(
            "su2",
            pkg_spec="su2@8.2.0 +mpi +openmp",
            compiler="gcc12",
        )
        required_package("su2")

    # Input deck archived from https://github.com/su2code/Tutorials/tree/d7991cb74e9e12a08463c579add6a9bf73713628/compressible_flow/Inviscid_Bump
    input_file(
        "inv_channel",
        url=f"file://{os.getcwd()}/inv_channel.tgz",
        sha256="1e65ec94bd52a31db344ec4778d96e2574c0acd244731a63048954876a35d4de",
        description="input deck used in https://su2code.github.io/tutorials/Inviscid_Bump",
    )

    executable("link-inputs", template=["ln -s {input_path}/* ."])

    executable(
        "execute",
        template=["{su2_executable} {input_config}"],
        use_mpi=True,
    )

    workload(
        "inv_channel",
        executables=["link-inputs", "execute"],
        input="inv_channel",
    )

    workload_group("all_workloads", workloads=["inv_channel"])

    workload_variable(
        "input_path",
        default="{inv_channel}",
        description="Path to the input for experiments",
        workload="inv_channel",
    )

    workload_variable(
        "input_config",
        default="inv_channel.cfg",
        description="Name of the input configuration file",
        workload="inv_channel",
    )

    workload_variable(
        "su2_executable",
        default="SU2_CFD",
        description="Path to the SU2 executable",
        workload_group="all_workloads",
    )

    # This is only used if using the SU2 parallel wrapper like parallel_computation.py
    environment_variable(
        "SU2_MPI_COMMAND",
        value="{mpi_command} -n %i %s",
        description="custom mpi command used by the wrapper",
        workload_group="all_workloads",
    )

    # The two env vars won't be needed after
    # https://github.com/spack/spack/pull/50495 is merged.
    environment_variable(
        "SU2_RUN",
        value="{su2_path}/bin",
        description="SU2 bin path",
        workload_group="all_workloads",
    )

    environment_variable(
        "SU2_HOME",
        value="{su2_path}",
        description="SU2 package prefix",
        workload_group="all_workloads",
    )

    success_criteria("completion", mode="string", match=".*?Exit Success")

    figure_of_merit(
        "Version",
        fom_regex=r".*?Release\s+(?P<version>[0-9\.]+)",
        group_name="version",
        units="",
        fom_type=FomType.INFO,
    )

    figure_of_merit(
        "Average seconds per iteration",
        fom_regex=r".*?Avg. s/iter:\s+(?P<avg_sec_per_iter>[0-9\.]+)",
        group_name="avg_sec_per_iter",
        units="s",
        fom_type=FomType.TIME,
    )
