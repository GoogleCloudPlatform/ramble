# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.appkit import *


class Orca(ExecutableApplication):
    """Define the ORCA application.

    For more details, see https://www.faccts.de/orca/.
    """

    name = "orca"

    tags = ["quantum chemistry"]

    software_spec("orca", pkg_spec="orca@5.0.4", package_manager="spack*")
    software_spec(
        "openmpi412", pkg_spec="openmpi@4.1.2", package_manager="spack*"
    )

    input_file(
        "orca_in",
        # Assumes the presence of an example_deck in cwd
        url=f"file://{os.path.join(os.getcwd(), 'example_deck.tar.gz')}",
        description="Input deck archive for ORCA",
    )

    tmp_file_patt1 = os.path.join("{scratch_dir}", "*_Compound_*")
    tmp_file_patt2 = os.path.join("{scratch_dir}", "*txt")
    executable(
        "clear_prior_checkpoints",
        f"rm -f {tmp_file_patt1} {tmp_file_patt2}",
        use_mpi=False,
    )

    executable(
        "copy_input",
        f"cp -R {os.path.join('{input_path}', '*')} {{scratch_dir}}",
        use_mpi=False,
    )

    # The only way to configure total ranks launched is by changing the PAL nprocs keyword
    # in the main input file.
    scratch_in_path = os.path.join("{scratch_dir}", "{main_input_file}")
    executable(
        "configure_nprocs",
        f"sed -i 's/nprocs.*/nprocs {{n_ranks}}/' {scratch_in_path}",
        use_mpi=False,
    )

    # orca requires the full path when running in parallel
    orca_exec_path = os.path.join("{orca_path}", "bin", "orca")
    executable(
        "run_orca",
        f'{orca_exec_path} {scratch_in_path} "{{ompi_args}}"',
        use_mpi=False,
    )

    workload(
        "standard",
        executables=[
            "clear_prior_checkpoints",
            "copy_input",
            "configure_nprocs",
            "run_orca",
        ],
        input="orca_in",
    )
    workload_variable(
        "scratch_dir",
        default="{experiment_run_dir}",
        description="Scratch directory",
        workload="standard",
    )
    workload_variable(
        "input_path",
        default="{orca_in}",
        description="Path for the fetched input deck",
        workload="standard",
    )
    workload_variable(
        "main_input_file",
        default="inputfile.inp",
        description="Leaf name of the main input file",
        workload="standard",
    )
    workload_variable(
        "ompi_args",
        default="",
        description="Extra openmpi args supplied to orca",
        workload="standard",
    )

    figure_of_merit(
        "Total run time",
        fom_regex=r"^\s*TOTAL RUN TIME:\s*(?P<time_str>.*)",
        group_name="time_str",
        units="",
    )

    success_criteria(
        "Error free",
        mode="string",
        anti_match=r".*Error:.*",
    )
    success_criteria(
        "Normal termination",
        mode="string",
        match=r".*ORCA TERMINATED NORMALLY.*",
    )
