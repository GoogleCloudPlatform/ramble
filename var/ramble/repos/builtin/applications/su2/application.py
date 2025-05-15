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
        define_compiler(
            "gcc14", pkg_spec="gcc@14.2.0", compiler_spec="gcc@14.2.0"
        )
        # TODO: intel-mpi doesn't work yet, probably need some package-level tweak
        software_spec("ompi5", pkg_spec="openmpi@5.0.5")
        software_spec(
            "su2",
            pkg_spec="su2@8.0.1 +mpi",
            compiler="gcc14",
        )
        required_package("su2")

    # Input deck archived from https://github.com/su2code/Tutorials/tree/d7991cb74e9e12a08463c579add6a9bf73713628/compressible_flow/Inviscid_Bump
    input_file(
        "inv_channel",
        url=f"file://{os.getcwd()}/inv_channel.tgz",
        sha256="1e65ec94bd52a31db344ec4778d96e2574c0acd244731a63048954876a35d4de",
        description="input deck used in https://su2code.github.io/tutorials/Inviscid_Bump",
    )

    executable(
        "link-inputs", template=["ln -s {input_path}/* {experiment_run_dir}/."]
    )

    executable(
        "execute",
        # Using the wrapper instead of invoking mpi command directly.
        # The wrapper performs some output file merging.
        template=["parallel_computation.py -f {input_config} -n {n_ranks}"],
        use_mpi=False,
    )

    workload(
        "inv_channel",
        executables=["link-inputs", "execute"],
        input="inv_channel",
    )

    workload_variable(
        "input_path",
        default="{inv_channel}",
        description="Path to the input for experiments",
        workloads=["inv_channel"],
    )

    workload_variable(
        "input_config",
        default="inv_channel.cfg",
        description="Name of the input configuration file",
        workloads=["inv_channel"],
    )

    environment_variable(
        "SU2_MPI_COMMAND",
        value="{mpi_command} -n %i %s",
        description="custom mpi command used by the wrapper",
        workloads=["*"],
    )

    # The two env vars won't be needed after
    # https://github.com/spack/spack/pull/50495 is merged.
    environment_variable(
        "SU2_RUN",
        value="{su2_path}/bin",
        description="SU2 bin path",
        workloads=["*"],
    )

    environment_variable(
        "SU2_HOME",
        value="{su2_path}",
        description="SU2 package prefix",
        workloads=["*"],
    )

    success_criteria("completion", mode="string", match=".*?Exit Success")

    # TODO: add in FOMs around solver iteration time
    # Currently such solver times are not generated to the output.
    figure_of_merit(
        "Solution postprocessing time",
        fom_regex=r"\s*Completed in (?P<time>\d+(\.\d+)) seconds",
        group_name="time",
        units="s",
        fom_type=FomType.TIME,
    )
