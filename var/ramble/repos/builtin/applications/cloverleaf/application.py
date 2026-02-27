# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import os

from ramble.appkit import *
from ramble.expander import Expander


class Cloverleaf(ExecutableApplication):
    """Define CLOVERLEAF application"""

    name = "cloverleaf"

    maintainers("rfbgo")

    tags("cfd", "euler", "mini-app")

    version("1.1", "Version 1.1 of CLOVERLEAF", preferred=True)

    with when("package_manager_family=spack"):
        define_compiler("gcc12", pkg_spec="gcc@12.2.0")

        software_spec(
            "ompi414",
            pkg_spec="openmpi@4.1.4 +legacylaunchers +cxx",
            compiler="gcc12",
        )
        software_spec(
            "cloverleaf-{application_version}",
            pkg_spec="cloverleaf@{application_version} build=ref",
            compiler="gcc12",
        )

        required_package("cloverleaf")

    executable("execute", "clover_leaf", use_mpi=True)

    stage_files(
        name="stage-input",
        src="{cloverleaf_path}/doc/tests/clover_{workload_name}.in",
        dst="{experiment_run_dir}/clover.in",
    )

    stage_files(
        name="stage-default-input",
        src="{cloverleaf_path}/doc/tests/clover.in",
        dst="{experiment_run_dir}/clover.in",
    )

    workload("bm_short_c", executables=["stage-input", "execute"])
    workload("bm_short", executables=["stage-input", "execute"])
    workload("qa", executables=["stage-input", "execute"])
    workload("sodbig", executables=["stage-input", "execute"])
    workload("sodx", executables=["stage-input", "execute"])
    workload("sodxy", executables=["stage-input", "execute"])
    workload("sody", executables=["stage-input", "execute"])
    workload("clover", executables=["stage-default-input", "execute"])

    # 2 through 8K
    for k in range(1, 14):
        workload("bm" + str(2**k), executables=["stage-input", "execute"])

    # 2 through 8K
    for k in range(1, 14):
        workload(
            "bm" + str(2**k) + "_short", executables=["stage-input", "execute"]
        )

    # 1 through 16K
    for k in range(15):
        workload(
            "bm" + str(2**k) + "s_short",
            executables=["stage-input", "execute"],
        )

    log_str = os.path.join(
        Expander.expansion_str("experiment_run_dir"), "clover.out"
    )

    floating_point_regex = r"[\+\-]*[0-9]*\.*[0-9]+E*[\+\-]*[0-9]*"

    step_count_regex = (
        r"\s*Step\s+(?P<step>[0-9]+).*\s+timestep\s+(?P<timestep>"
        + floating_point_regex
        + r")"
    )

    wall_clock_regex = r"\s*Wall clock\s+(?P<wall_clock>[0-9]+\.[0-9]+)"

    figure_of_merit(
        "Timestep",
        log_file=log_str,
        fom_regex=step_count_regex,
        group_name="timestep",
        units="s",
        contexts=["step"],
    )

    figure_of_merit(
        "Wall Clock",
        log_file=log_str,
        fom_regex=wall_clock_regex,
        group_name="wall_clock",
        units="s",
        contexts=["step"],
    )

    figure_of_merit_context(
        "step", regex=step_count_regex, output_format="Step {step}"
    )

    step_summary_regex = (
        r"\s*step:\s+(?P<step>[0-9]+)\s+"
        + r"(?P<volume>"
        + floating_point_regex
        + r")\s+"
        + r"(?P<mass>"
        + floating_point_regex
        + r")\s+"
        + r"(?P<density>"
        + floating_point_regex
        + r")\s+"
        + r"(?P<pressure>"
        + floating_point_regex
        + r")\s+"
        + r"(?P<internal_energy>"
        + floating_point_regex
        + r")\s+"
        + r"(?P<kinetic_energy>"
        + floating_point_regex
        + r")\s+"
        + r"(?P<total_energy>"
        + floating_point_regex
        + r")"
    )

    figure_of_merit(
        "Total step count",
        log_file=log_str,
        fom_regex=step_summary_regex,
        group_name="step",
        units="",
    )

    figure_of_merit(
        "Final Kinetic Energy",
        log_file=log_str,
        fom_regex=step_summary_regex,
        group_name="kinetic_energy",
        units="Joules",
    )

    figure_of_merit(
        "Total Elapsed Time",
        log_file=log_str,
        fom_regex=wall_clock_regex,
        group_name="wall_clock",
        units="s",
    )

    figure_of_merit(
        "First step overhead",
        log_file=log_str,
        fom_regex=(
            r"\s*First step overhead\s+(?P<overhead>"
            + floating_point_regex
            + r")"
        ),
        group_name="overhead",
        units="s",
    )
