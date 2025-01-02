# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Roms(ExecutableApplication):
    """
    The Regional Ocean Modeling System (ROMS) is a free-surface,
    terrain-following, primitive equations ocean model widely used by the
    scientific community for a diverse range of applications. ROMS includes
    accurate and efficient physical and numerical algorithms and several
    coupled models for biogeochemical, bio-optical, sediment, and sea ice
    applications.

    https://www.myroms.org/
    """

    name = "roms"

    tags("ocean")

    software_spec("roms", pkg_spec="roms@4.1", package_manager="spack*")
    software_spec(
        "openmpi412", pkg_spec="openmpi@4.1.2", package_manager="spack*"
    )

    input_file(
        "bm1",
        url="https://raw.githubusercontent.com/myroms/roms/refs/tags/roms-4.1/ROMS/External/roms_benchmark1.in",
        expand=False,
        description="Simple test benchmark (small)",
    )
    input_file(
        "varinfo",
        url="https://raw.githubusercontent.com/myroms/roms/refs/tags/roms-4.1/ROMS/External/varinfo.yaml",
        expand=False,
        description="Metadata dict for benchmark inputs",
    )

    executable("execute", "romsM {input_deck}", use_mpi=True)

    executable(
        "copy_input", "cp {input_path} {experiment_run_dir}/.", use_mpi=False
    )

    executable(
        "copy_varinfo",
        template=[
            "mkdir -p {experiment_run_dir}/ROMS/External/",
            "cp {varinfo} {experiment_run_dir}/ROMS/External/",
        ],
        use_mpi=False,
    )

    workload(
        "benchmark_1",
        executables=["copy_input", "copy_varinfo", "execute"],
        inputs=["bm1", "varinfo"],
    )

    workload_variable(
        "input_deck",
        default="roms_benchmark1.in",
        description="Name of input deck",
        workloads=["benchmark_1"],
    )

    workload_variable(
        "input_path",
        default="{bm1}",
        description="Path to input deck",
        workloads=["benchmark_1"],
    )

    success_criteria(
        "prints_done",
        mode="string",
        match=r".*ROMS/TOMS: DONE.*",
    )

    figure_of_merit(
        "Total Time",
        fom_regex=r"\s*All percentages are with respect to total time =\s+(?P<time>\d+\.\d+).*",
        group_name="time",
        units="s",
    )
