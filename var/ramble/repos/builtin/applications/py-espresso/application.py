# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class PyEspresso(ExecutableApplication):
    """Define py-espresso (pypresso) application

    ESPResSo is a highly versatile software package for performing and analyzing scientific Molecular Dynamics many-particle simulations of "coarse-grained" bead-spring models as they are used in soft-matter research in physics, chemistry and molecular biology. It can be used to simulate systems as for example polymers, liquid crystals, colloids, ferrofluids and biological systems such as DNA and lipid membranes.
    """

    name = "py-espresso"

    tags("molecular-dynamics", "python")

    with when("package_manager_family=spack"):
        software_spec(
            "py-espresso",
            pkg_spec="py-espresso@4.2.2",
        )

    with when("package_manager_family=eessi"):
        software_spec(
            "py-espresso",
            pkg_spec="ESPResSo/4.2.2-foss-2023b",
        )

    executable("execute", template=["pypresso {input_file}"], use_mpi=True)

    input_file(
        "particle_sample_input",
        url="https://raw.githubusercontent.com/espressomd/espresso/refs/tags/4.2.2/samples/p3m.py",
        expand=False,
        description="Sample p3m input",
    )

    workload("p3m", executables=["execute"], inputs=["particle_sample_input"])

    workload_variable(
        "input_file",
        default="{particle_sample_input}",
        description="Input file to run",
        workloads=["p3m"],
    )

    integration_regex = (
        r"Start integration: run (?P<iter>\d+) times (?P<steps>\d+) steps"
    )
    figure_of_merit(
        "iterations", group_name="iter", fom_regex=integration_regex, units=""
    )
    figure_of_merit(
        "steps", group_name="steps", fom_regex=integration_regex, units=""
    )
