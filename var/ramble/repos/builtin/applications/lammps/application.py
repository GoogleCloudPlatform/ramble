# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.appkit import *


class Lammps(ExecutableApplication):
    """Define LAMMPS application"""

    name = "lammps"

    maintainers("douglasjacobsen")

    tags("molecular-dynamics", "hpc-benchmark")

    define_compiler("gcc9", pkg_spec="gcc@9.3.0")

    workload_group("all_workloads", workloads=[])
    workload_group("standard_workloads", workloads=[])
    workload_group("configured_workloads", workloads=[])
    workload_group("intel_workloads", workloads=[])

    workload_variable(
        "intel_test_path",
        default=os.path.join("{lammps-stage}", "src", "INTEL", "TEST"),
        description="Path for Intel Test files",
        workload_group="all_workloads",
    )

    workload_variable(
        "examples_path",
        default=os.path.join("{lammps-stage}", "examples"),
        description="Path for example files",
        workload_group="all_workloads",
    )

    workload_variable(
        "input_path",
        default=os.path.join("{intel_test_path}", "in.{workload_name}"),
        description="Path to input file",
        workload_group="intel_workloads",
    )

    workload_variable(
        "input_stage",
        default="stable_23Jun2022_update3",
        description="Stage name of LAMMPS input archive",
        workload_group="all_workloads",
    )

    workload_variable(
        "input_path",
        default=os.path.join("{intel_test_path}", "in.{workload_name}"),
        description="Path to input file for workload",
        workload_group="intel_workloads",
    )

    workload_variable(
        "input_path",
        default="{workload_input_dir}/in.{workload_name}.txt",
        description="Path for the workload input file.",
        workload_group="standard_workloads",
    )

    workload_variable(
        "lammps_flags",
        default="",
        description="Additional execution flags for lammps",
        workload_group="all_workloads",
    )

    with when("package_manager_family=spack"):
        software_spec("intel-mpi", pkg_spec="intel-oneapi-mpi@2021.13.1")

        software_spec(
            "lammps",
            pkg_spec="lammps@20220623.4 +opt+manybody+molecule+kspace+rigid+openmp+openmp-package+asphere+dpd-basic+dpd-meso+dpd-react+dpd-smooth",
            compiler="gcc9",
        )

        required_package("lammps")

    input_file(
        "leonard-jones",
        url="https://www.lammps.org/inputs/in.lj.txt",
        expand=False,
        sha256="874b4c63b6fcbb6ede76522df19087acf2f49b6bc96794cf0aa3218c66ff7e06",
        description="Atomic fluid. 32k atoms. 100 timesteps. https://www.lammps.org/bench.html#lj",
    )
    input_file(
        "eam",
        url="https://www.lammps.org/inputs/in.eam.txt",
        expand=False,
        sha256="2fa09183c626c34570cc367384fe4c297ab153521adb3ea44ff7e265d451ad75",
        description="Cu metallic solid with embedded atom method potential. 32k atoms. https://www.lammps.org/bench.html#eam",
    )
    input_file(
        "polymer-chain-melt",
        url="https://www.lammps.org/inputs/in.chain.txt",
        expand=False,
        sha256="97676f19d2d791c42415698c354a18b26a3cbe4006cd2161cf8924415d9f7c82",
        description="Bead-spring polymer melt with 100-mer chains and FENE bonds. 32k atoms. 100 timesteps. https://www.lammps.org/bench.html#chain",
    )
    input_file(
        "chute",
        url="https://www.lammps.org/inputs/in.chute.txt",
        expand=False,
        sha256="91e1743cc39365b32757cfb3c76399f5ed8debad0b890cb36ee7bdf47d2dfd2d",
        description="Chute flow of packed granular particles with frictional history potential. 32k atoms. 100 timeteps. https://www.lammps.org/bench.html#chute",
    )
    input_file(
        "rhodo",
        url="https://www.lammps.org/inputs/in.rhodo.txt",
        expand=False,
        sha256="4b6cc70db1b8fe269c48b8e06749f144f400e9a4054bf180ac9b1b9a5a5bb07f",
        description="All-atom rhodopsin protein in solvated lipid bilayer with CHARMM force field, long-range Coulombics via PPPM (particle-particle particle mesh), SHAKE constraints. This model contains counter-ions and a reduced amount of water to make a 32K atom system. 32k atoms. 100 timesteps. https://www.lammps.org/bench.html#rhodo",
    )

    input_file(
        "lammps-stage",
        url="https://github.com/lammps/lammps/archive/refs/tags/{input_stage}.tar.gz",
        target_dir="{application_input_dir}/lammps-input-stage",
        description="Stage of lammps source from release",
    )
    executable(
        "copy",
        template=["cp {input_path} {experiment_run_dir}/input.txt"],
        use_mpi=False,
    )
    executable(
        "configure-reaxff",
        template=[
            "sed -i -e 's/x index .*/x index {x}/g' -i input.txt",
            "sed -i -e 's/y index .*/y index {y}/g' -i input.txt",
            "sed -i -e 's/z index .*/z index {z}/g' -i input.txt",
            "sed -i -e 's/y index .*/y index {timesteps}/g' -i input.txt",
        ],
        use_mpi=False,
    )

    executable(
        "configure-size-scale",
        template=[
            "sed -i -e 's/xx equal .*/xx equal {xx}/g' -i input.txt",
            "sed -i -e 's/yy equal .*/yy equal {yy}/g' -i input.txt",
            "sed -i -e 's/zz equal .*/zz equal {zz}/g' -i input.txt",
        ],
        use_mpi=False,
    )
    executable(
        "configure-run-timesteps",
        template=[
            "sed 's/run.*[0-9]+/run\t\t{timesteps}/g' -i input.txt",
        ],
        use_mpi=False,
    )

    executable(
        "configure-timestep-variables",
        template=[
            "sed 's/t index .*[0-9]+/t index {main_timesteps}/g' -i input.txt",
            "sed 's/w index .*[0-9]+/t index {warmup_timesteps}/g' -i input.txt",
            "sed 's/m index .*[0-9]+/t index {timestep_multiplier}/g' -i input.txt",
        ],
        use_mpi=False,
    )

    exec_path = os.path.join("{lammps_path}", "bin", "lmp")

    executable(
        "execute",
        f"{exec_path}" + " -i input.txt {lammps_flags}",
        use_mpi=True,
    )

    executable(
        "set-data-path",
        template=[
            r"sed 's|data\.|"
            + os.path.join("{lammps-stage}", "bench", "data.")
            + "|g' -i input.txt"
        ],
        use_mpi=False,
    )

    executable(
        "change-root",
        template=[
            "sed 's|${root}|{lammps-stage}" + os.path.sep + "|g' -i input.txt"
        ],
        use_mpi=False,
    )

    executable(
        "copy-cube",
        template=[
            "cp "
            + os.path.join("{intel_test_path}", "mW*.data")
            + " {experiment_run_dir}"
            + os.path.sep
            + "."
            "cp "
            + os.path.join("{intel_test_path}", "mW.sw")
            + " {experiment_run_dir}"
            + os.path.sep
            + "."
        ],
        use_mpi=False,
    )

    executable(
        "copy-contents",
        template=[
            "cp {input_path}/* {experiment_run_dir}/.",
            "cp {input_file} input.txt",
        ],
        use_mpi=False,
    )

    workload(
        "lj",
        executables=[
            "copy",
            "configure-size-scale",
            "configure-run-timesteps",
            "execute",
        ],
        input="leonard-jones",
    )
    with default_args(workloads=["lj"]):
        workload_group("all_workloads", mode="append")
        workload_group("standard_workloads", mode="append")
        workload_variable(
            "timesteps",
            default="100",
            description="Number of timesteps",
        )
        workload_variable(
            "xx",
            default="20*$x",
            description="xx value",
        )
        workload_variable(
            "yy",
            default="20*$y",
            description="yy value",
        )
        workload_variable(
            "zz",
            default="20*$z",
            description="zz value",
        )

    workload(
        "eam",
        executables=[
            "copy",
            "configure-size-scale",
            "configure-run-timesteps",
            "execute",
        ],
        input="eam",
    )
    with default_args(workloads=["eam"]):
        workload_group("all_workloads", mode="append")
        workload_group("standard_workloads", mode="append")
        workload_variable(
            "timesteps",
            default="100",
            description="Number of timesteps",
        )
        workload_variable(
            "xx",
            default="20*$x",
            description="xx value",
        )
        workload_variable(
            "yy",
            default="20*$y",
            description="yy value",
        )
        workload_variable(
            "zz",
            default="20*$z",
            description="zz value",
        )

    workload(
        "chain",
        executables=[
            "copy",
            "set-data-path",
            "configure-run-timesteps",
            "execute",
        ],
        inputs=["polymer-chain-melt", "lammps-stage"],
    )
    with default_args(workloads=["chain"]):
        workload_group("all_workloads", mode="append")
        workload_group("standard_workloads", mode="append")
        workload_variable(
            "timesteps",
            default="100",
            description="Number of timesteps",
        )

    workload(
        "chute",
        executables=["copy", "configure-run-timesteps", "execute"],
        input="chute",
    )
    with default_args(workloads=["chute"]):
        workload_group("all_workloads", mode="append")
        workload_group("standard_workloads", mode="append")
        workload_variable(
            "timesteps",
            default="100",
            description="Number of timesteps",
        )

    workload(
        "rhodo",
        executables=["copy", "set-data-path", "execute"],
        inputs=["rhodo", "lammps-stage"],
    )
    with default_args(workloads=["rhodo"]):
        workload_group("all_workloads", mode="append")
        workload_group("standard_workloads", mode="append")
        workload_variable(
            "timesteps",
            default="100",
            description="Number of timesteps",
        )

    workload(
        "intel.airebo",
        executables=[
            "copy",
            "change-root",
            "configure-size-scale",
            "configure-timestep-variables",
            "execute",
        ],
        input="lammps-stage",
    )
    with default_args(workloads=["intel.airebo"]):
        workload_group("all_workloads", mode="append")
        workload_group("intel_workloads", mode="append")
        workload_variable(
            "warmup_timesteps",
            default="10",
            description="Number of warmup timesteps",
        )
        workload_variable(
            "main_timesteps",
            default="550",
            description="Number of main timesteps",
        )
        workload_variable(
            "timestep_multiplier",
            default="1",
            description="Multiplier for main timesteps",
        )
        workload_variable(
            "xx",
            default="17*$x",
            description="xx value",
        )
        workload_variable(
            "yy",
            default="16*$y",
            description="yy value",
        )
        workload_variable(
            "zz",
            default="2*$z",
            description="zz value",
        )

    workload(
        "intel.dpd",
        executables=[
            "copy",
            "change-root",
            "configure-size-scale",
            "configure-timestep-variables",
            "execute",
        ],
        input="lammps-stage",
    )
    with default_args(workloads=["intel.dpd"]):
        workload_group("all_workloads", mode="append")
        workload_group("intel_workloads", mode="append")
        workload_variable(
            "warmup_timesteps",
            default="10",
            description="Number of warmup timesteps",
        )
        workload_variable(
            "main_timesteps",
            default="4000",
            description="Number of main timesteps",
        )
        workload_variable(
            "timestep_multiplier",
            default="1",
            description="Multiplier for main timesteps",
        )
        workload_variable(
            "xx",
            default="20*$x",
            description="xx value",
        )
        workload_variable(
            "yy",
            default="20*$y",
            description="yy value",
        )
        workload_variable(
            "zz",
            default="20*$z",
            description="zz value",
        )

    workload(
        "intel.eam",
        executables=[
            "copy",
            "change-root",
            "configure-size-scale",
            "configure-timestep-variables",
            "execute",
        ],
        input="lammps-stage",
    )
    with default_args(workloads=["intel.eam"]):
        workload_group("all_workloads", mode="append")
        workload_group("intel_workloads", mode="append")
        workload_variable(
            "warmup_timesteps",
            default="10",
            description="Number of warmup timesteps",
        )
        workload_variable(
            "main_timesteps",
            default="3100",
            description="Number of main timesteps",
        )
        workload_variable(
            "timestep_multiplier",
            default="1",
            description="Multiplier for main timesteps",
        )
        workload_variable(
            "xx",
            default="20*$x",
            description="xx value",
        )
        workload_variable(
            "yy",
            default="20*$y",
            description="yy value",
        )
        workload_variable(
            "zz",
            default="20*$z",
            description="zz value",
        )

    workload(
        "intel.lc",
        executables=[
            "copy",
            "change-root",
            "configure-timestep-variables",
            "execute",
        ],
        input="lammps-stage",
    )
    with default_args(workloads=["intel.lc"]):
        workload_group("all_workloads", mode="append")
        workload_group("intel_workloads", mode="append")
        workload_variable(
            "warmup_timesteps",
            default="10",
            description="Number of warmup timesteps",
        )
        workload_variable(
            "main_timesteps",
            default="8400",
            description="Number of main timesteps",
        )
        workload_variable(
            "timestep_multiplier",
            default="1",
            description="Multiplier for main timesteps",
        )

    workload(
        "intel.lj",
        executables=[
            "copy",
            "change-root",
            "configure-size-scale",
            "configure-timestep-variables",
            "execute",
        ],
        input="lammps-stage",
    )
    with default_args(workloads=["intel.lj"]):
        workload_group("all_workloads", mode="append")
        workload_group("intel_workloads", mode="append")
        workload_variable(
            "warmup_timesteps",
            default="10",
            description="Number of warmup timesteps",
        )
        workload_variable(
            "main_timesteps",
            default="7900",
            description="Number of main timesteps",
        )
        workload_variable(
            "timestep_multiplier",
            default="1",
            description="Multiplier for main timesteps",
        )
        workload_variable(
            "xx",
            default="20*$x",
            description="xx value",
        )
        workload_variable(
            "yy",
            default="20*$y",
            description="yy value",
        )
        workload_variable(
            "zz",
            default="20*$z",
            description="zz value",
        )

    workload(
        "intel.rhodo",
        executables=[
            "copy",
            "change-root",
            "configure-timestep-variables",
            "execute",
        ],
        input="lammps-stage",
    )
    with default_args(workloads=["intel.rhodo"]):
        workload_group("all_workloads", mode="append")
        workload_group("intel_workloads", mode="append")
        workload_variable(
            "warmup_timesteps",
            default="10",
            description="Number of warmup timesteps",
        )
        workload_variable(
            "main_timesteps",
            default="520",
            description="Number of main timesteps",
        )
        workload_variable(
            "timestep_multiplier",
            default="1",
            description="Multiplier for main timesteps",
        )

    workload(
        "intel.sw",
        executables=[
            "copy",
            "change-root",
            "configure-size-scale",
            "configure-timestep-variables",
            "execute",
        ],
        input="lammps-stage",
    )
    with default_args(workloads=["intel.sw"]):
        workload_group("all_workloads", mode="append")
        workload_group("intel_workloads", mode="append")
        workload_variable(
            "warmup_timesteps",
            default="10",
            description="Number of warmup timesteps",
        )
        workload_variable(
            "main_timesteps",
            default="6200",
            description="Number of main timesteps",
        )
        workload_variable(
            "timestep_multiplier",
            default="1",
            description="Multiplier for main timesteps",
        )
        workload_variable(
            "xx",
            default="20*$x",
            description="xx value",
        )
        workload_variable(
            "yy",
            default="20*$y",
            description="yy value",
        )
        workload_variable(
            "zz",
            default="10*$z",
            description="zz value",
        )

    workload(
        "intel.tersoff",
        executables=[
            "copy",
            "change-root",
            "configure-size-scale",
            "configure-timestep-variables",
            "execute",
        ],
        input="lammps-stage",
    )
    with default_args(workloads=["intel.tersoff"]):
        workload_group("all_workloads", mode="append")
        workload_group("intel_workloads", mode="append")
        workload_variable(
            "warmup_timesteps",
            default="10",
            description="Number of warmup timesteps",
        )
        workload_variable(
            "main_timesteps",
            default="2420",
            description="Number of main timesteps",
        )
        workload_variable(
            "timestep_multiplier",
            default="1",
            description="Multiplier for main timesteps",
        )
        workload_variable(
            "xx",
            default="20*$x",
            description="xx value",
        )
        workload_variable(
            "yy",
            default="20*$y",
            description="yy value",
        )
        workload_variable(
            "zz",
            default="10*$z",
            description="zz value",
        )

    workload(
        "intel.water",
        executables=[
            "copy",
            "change-root",
            "configure-timestep-variables",
            "execute",
        ],
        input="lammps-stage",
    )
    with default_args(workloads=["intel.water"]):
        workload_group("all_workloads", mode="append")
        workload_group("intel_workloads", mode="append")
        workload_variable(
            "warmup_timesteps",
            default="10",
            description="Number of warmup timesteps",
        )
        workload_variable(
            "main_timesteps",
            default="2600",
            description="Number of main timesteps",
        )
        workload_variable(
            "timestep_multiplier",
            default="1",
            description="Multiplier for main timesteps",
        )

    workload(
        "hns-reaxff",
        executables=["copy-contents", "configure-reaxff", "execute"],
        inputs=["lammps-stage"],
    )
    with default_args(workloads=["hns-reaxff"]):
        workload_group("all_workloads", mode="append")

        workload_variable(
            "input_path",
            default=os.path.join(
                "{examples_path}", "reaxff", "HNS", "in.{workload_name}"
            ),
            description="Path to input file for workload",
        )

        workload_variable(
            "input_file",
            default="in.reaxff.hns",
            description="hns-reaxff input file name",
        )

        workload_variable(
            "timesteps",
            default="100",
            description="Number of timesteps",
        )
        workload_variable(
            "x",
            default="2",
            description="x value",
        )
        workload_variable(
            "y",
            default="2",
            description="y value",
        )
        workload_variable(
            "z",
            default="2",
            description="z value",
        )

    success_criteria(
        "walltime",
        mode="string",
        match=r"\s*Total wall time",
        file="{log_file}",
    )

    figure_of_merit(
        "Total wall time",
        fom_regex=r"Total wall time.*\s+(?P<walltime>[0-9:]+)",
        group_name="walltime",
        units="",
        fom_type=FomType.TIME,
    )
    figure_of_merit(
        "Nanoseconds per day",
        fom_regex=r"Performance.*?\s+(?P<nspd>[0-9\.]+) (ns|tau)/day",
        group_name="nspd",
        units="ns/day",
        fom_type=FomType.THROUGHPUT,
    )
    figure_of_merit(
        "Hours per nanosecond",
        fom_regex=r"Performance.*?\s+(?P<hpns>[0-9\.]+) hours/ns",
        group_name="hpns",
        units="hours/ns",
        fom_type=FomType.TIME,
    )
    figure_of_merit(
        "Timesteps per second",
        fom_regex=r"Performance.*?\s+(?P<tsps>[0-9\.]+) timesteps/s",
        group_name="tsps",
        units="timesteps/s",
        fom_type=FomType.THROUGHPUT,
    )

    figure_of_merit(
        "Number of Atoms",
        fom_regex=r"Loop.*with (?P<atoms>[0-9]+) atoms",
        group_name="atoms",
        units="",
        fom_type=FomType.INFO,
    )

    for func_name in ["Pair", "Neigh", "Comm", "Output", "Modifier"]:
        func_time_regex = (
            func_name
            + r"\s+\|\s+(?P<min_time>\S+)\s+\|\s+(?P<avg_time>\S+)\s+\|\s+(?P<max_time>\S+)\s+\|\s+(?P<avg_var>\S+)\s+\|\s+(?P<total_pct>\S+)"
        )
        figure_of_merit(
            f"{func_name} min time",
            fom_regex=func_time_regex,
            group_name="min_time",
            units="s",
        )

        figure_of_merit(
            f"{func_name} avg time",
            fom_regex=func_time_regex,
            group_name="avg_time",
            units="s",
        )

        figure_of_merit(
            f"{func_name} max time",
            fom_regex=func_time_regex,
            group_name="max_time",
            units="s",
        )

        figure_of_merit(
            f"{func_name} avg. variance",
            fom_regex=func_time_regex,
            group_name="avg_var",
            units="",
        )

        figure_of_merit(
            f"{func_name} percent of runtime",
            fom_regex=func_time_regex,
            group_name="total_pct",
            units="%",
        )
