# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Openmm(ExecutableApplication):
    """OpenMM is a toolkit for molecular simulation. It can be used either as a
    stand-alone application for running simulations, or as a library you call
    from your own code.

    https://github.com/openmm/openmm
    """

    name = "openmm"

    tags("molecular-dynamics", "machine-learning", "hpc-benchmark")

    maintainers("rfbgo")

    # Define pip software requirement
    with when("package_manager_family=pip"):
        software_spec(
            "openmm",
            pkg_spec="openmm",
        )
        required_package("openmm")

    # Define spack software requirement
    with when("package_manager_family=spack"):
        software_spec(
            "openmm",
            pkg_spec="openmm",
        )
        required_package("openmm")

    # Official OpenMM benchmark script
    input_file(
        "benchmark_script",
        url="https://raw.githubusercontent.com/openmm/openmm/master/examples/benchmarks/benchmark.py",
        description="OpenMM official simulation benchmark script",
        expand=False,
    )

    input_file(
        "5dfr_minimized",
        url="https://raw.githubusercontent.com/openmm/openmm/master/examples/benchmarks/5dfr_minimized.pdb",
        description="5dfr minimized structure for NoCutoff benchmarks",
        expand=False,
    )

    input_file(
        "5dfr_solv_cube_equil",
        url="https://raw.githubusercontent.com/openmm/openmm/master/examples/benchmarks/5dfr_solv-cube_equil.pdb",
        description="5dfr solvated structure for PME benchmarks",
        expand=False,
    )

    input_file(
        "apoa1",
        url="https://raw.githubusercontent.com/openmm/openmm/master/examples/benchmarks/apoa1.pdb",
        description="ApoA1 structure for ApoA1 benchmarks",
        expand=False,
    )

    # Executable for running the standard OpenMM benchmark
    executable(
        "run_benchmark",
        "ln -sf {5dfr_minimized} 5dfr_minimized.pdb && "
        "ln -sf {5dfr_solv_cube_equil} 5dfr_solv-cube_equil.pdb && "
        "ln -sf {apoa1} apoa1.pdb && "
        "python3 {benchmark_path} "
        "--platform {openmm_platform} "
        "--test {benchmark_test} "
        "{extra_args}",
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    # Workload definition
    workload(
        "benchmark",
        executable="run_benchmark",
        inputs=[
            "benchmark_script",
            "5dfr_minimized",
            "5dfr_solv_cube_equil",
            "apoa1",
        ],
    )

    # Workload variables
    workload_variable(
        "benchmark_path",
        default="{benchmark_script}",
        description="Path to the OpenMM benchmark script",
        workload="benchmark",
    )

    workload_variable(
        "openmm_platform",
        default="OpenCL",
        values=["Reference", "CPU", "OpenCL", "CUDA"],
        description="OpenMM compute platform to execute on",
        workload="benchmark",
    )

    workload_variable(
        "benchmark_test",
        default="pme",
        values=[
            "gbsa",
            "rf",
            "pme",
            "apoa1rf",
            "apoa1pme",
            "amoebagbsa",
            "amoebapme",
        ],
        description="Benchmark simulation test deck",
        workload="benchmark",
    )

    workload_variable(
        "extra_args",
        default="--seconds 60",
        description="Additional arguments for benchmark.py (e.g., --seconds or --steps)",
        workload="benchmark",
    )

    # Figures of Merit
    figure_of_merit(
        "Simulation Throughput",
        log_file="{log_file}",
        fom_regex=r"(?:.*Median\s+daily\s+throughput:\s+|.*ns_per_day:\s+)(?P<throughput>[0-9\.]+).*",
        group_name="throughput",
        units="ns/day",
        fom_type=FomType.THROUGHPUT,
    )

    figure_of_merit(
        "Elapsed Time",
        log_file="{log_file}",
        fom_regex=r"(?:.*elapsed_time:\s+|.*Test\s+time:\s+)(?P<time>[0-9\.]+).*",
        group_name="time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "Executed Steps",
        log_file="{log_file}",
        fom_regex=r".*steps:\s+(?P<steps>[0-9]+).*",
        group_name="steps",
        units="steps",
        fom_type=FomType.THROUGHPUT,
    )

    # Success Criteria
    success_criteria(
        "benchmark_success",
        mode="string",
        match=r".*(?:Median\s+daily\s+throughput:|ns_per_day:).*",
        file="{log_file}",
    )
