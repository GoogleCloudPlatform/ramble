# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.appkit import *
from ramble.expander import Expander


class Ngspice(ExecutableApplication):
    """Define NgSpice application"""

    name = "ngspice"

    maintainers("vishalbh")

    tags("circuit-simulation", "mini-app")

    with when("package_manager_family=spack"):
        define_compiler("gcc12", pkg_spec="gcc@12.2.0")

        software_spec(
            "ngspice",
            pkg_spec="ngspice@44 build=bin",
            compiler="gcc12",
        )

        required_package("ngspice")

    input_file(
        "Ngspice_BenchMark_Inputs",
        url="http://www.phoronix-test-suite.com/benchmark-files/iscas85Circuits-1.tar.xz",
        sha256="5d160b3496e95fa4861558b95388bf346c914216e1c3b29690d2573f88df6892",
        description="Input files for the ngspice workload",
        target_dir="{experiment_run_dir}",
    )

    out_file = os.path.join(
        Expander.expansion_str("experiment_run_dir"),
        Expander.expansion_str("workload_name") + ".out",
    )

    executable(
        "execute",
        "ngspice -b {input_file} -o " + out_file,
        use_mpi=True,
    )

    all_workloads = [
        "c1355",
        "c1908",
        "c2670",
        "c3540",
        "c432",
        "c499",
        "c6288",
        "c7552",
        "c880",
    ]
    for normal_workload in all_workloads:
        workload(
            normal_workload,
            executables=["execute"],
            inputs=["Ngspice_BenchMark_Inputs"],
        )
        workload_variable(
            "input_file",
            default="iscas85Circuits-1/85/"
            + normal_workload
            + "/"
            + normal_workload
            + ".net",
            description="Path to input file for  "
            + normal_workload
            + " workload",
            workloads=[normal_workload],
        )

    for ann_workload in all_workloads:
        workload(
            ann_workload + "_ann",
            executables=["execute"],
            inputs=["Ngspice_BenchMark_Inputs"],
        )
        workload_variable(
            "input_file",
            default="iscas85Circuits-1/85/"
            + ann_workload
            + "/"
            + ann_workload
            + "_ann.net",
            description="Path to input file for  "
            + ann_workload
            + " workload",
            workloads=[ann_workload + "_ann"],
        )

    floating_point_regex = r"\d+\.\d+"
    total_analysis_regex = (
        r"Total\s*analysis\s*time\s*\(seconds\)\s*=\s*(?P<time>"
        + floating_point_regex
        + r")"
    )
    success_criteria(
        "valid", mode="string", match=total_analysis_regex, file=out_file
    )

    figure_of_merit(
        "Total Simulation Time",
        log_file=out_file,
        fom_regex=total_analysis_regex,
        group_name="time",
        units="s",
    )
