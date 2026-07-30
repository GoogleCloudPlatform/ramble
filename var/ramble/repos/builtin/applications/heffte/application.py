# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Heffte(ExecutableApplication):
    """
    The Highly Efficient FFT for Exascale (heFFTe) library delivers
    algorithms for distributed fast-Fourier transforms on heterogeneous
    systems.
    """

    name = "heffte"

    tags("fft-benchmark", "communication-benchmark")

    maintainers("tteggelit")

    version("2.4.1", "Version 2.4.1 of the heFFTe library", preferred=True)
    version("2.4.0", "Version 2.4.0 of the heFFTe library")
    version("2.3.0", "Version 2.3.0 of the heFFTe library")
    version("2.2.0", "Version 2.2.0 of the heFFTe library")
    version("2.1.0", "Version 2.1.0 of the heFFTe library")

    with when("package_manager_family=spack"):
        define_compiler("gcc14", pkg_spec="gcc@14.2.0")

        software_spec(
            "intel-mpi",
            pkg_spec="intel-oneapi-mpi@2021.17.2",
            compiler="gcc14",
        )

        software_spec(
            "heffte-{application::heffte::version}",
            pkg_spec="heffte@{application::heffte::version} "
            + "{application::variant::benchmarks} "
            + "{application::variant::fftw} "
            + "{application::variant::cuda} "
            + "{application::variant::mkl}",
            compiler="gcc14",
        )

        required_package("heffte")

    variant(
        "benchmarks",
        values=[True, False],
        default=True,
        description="Install the heFFTe benchmarks. Required to run benchmarks",
    )

    variant(
        "fftw",
        default=False,
        values=[True, False],
        description="fftw support variant",
    )

    variant(
        "cuda",
        default=False,
        values=[True, False],
        description="CUDA support variant",
    )

    variant(
        "mkl",
        default=False,
        values=[True, False],
        description="Intel MKL support variant",
    )

    executable(
        "c2c",
        "{heffte_path}/share/heffte/benchmarks/speed3d_c2c "
        + "{fft} "
        + "{precision} "
        + "{dim_x} "
        + "{dim_y} "
        + "{dim_z} "
        + "-{reorder} "
        + "-{reshape} "
        + "-n{num_runs} "
        + "-{comm_method}",
        use_mpi=True,
    )

    executable(
        "r2c",
        "{heffte_path}/share/heffte/benchmarks/speed3d_r2c "
        + "{fft} "
        + "{precision} "
        + "{dim_x} "
        + "{dim_y} "
        + "{dim_z} "
        + "-{reorder} "
        + "-{reshape} "
        + "-n{num_runs} "
        + "-{comm_method}",
        use_mpi=True,
    )

    with when("@2.2.0:"):
        executable(
            "convolution",
            "{heffte_path}/share/heffte/benchmarks/convolution "
            + "{fft} "
            + "{precision} "
            + "{dim_x} "
            + "{dim_y} "
            + "{dim_z} "
            + "-{reorder} "
            + "-{reshape} "
            + "-n{num_runs} "
            + "-{comm_method}",
            use_mpi=True,
        )

        executable(
            "r2r",
            "{heffte_path}/share/heffte/benchmarks/speed3d_r2r "
            + "{fft}-{r2r_transform} "
            + "{precision} "
            + "{dim_x} "
            + "{dim_y} "
            + "{dim_z} "
            + "-{reorder} "
            + "-{reshape} "
            + "-n{num_runs} "
            + "-{comm_method}",
            use_mpi=True,
        )

    workload(
        "c2c",
        executables=["c2c"],
    )

    workload(
        "r2c",
        executables=["r2c"],
    )

    with when("@2.2.0:"):
        workload(
            "convolution",
            executables=["convolution"],
        )

        workload(
            "r2r",
            executables=["r2r"],
        )

    workload_group(
        "3d_complex_workloads",
        workloads=[
            "c2c",
            "r2c",
        ],
    )

    with when("@:2.1.0"):
        workload_group(
            "all_workloads",
            workloads=[
                "c2c",
                "r2c",
            ],
        )
        workload_group(
            "3d_workloads",
            workloads=[
                "c2c",
                "r2c",
            ],
        )

    with when("@2.2.0:"):
        workload_group(
            "all_workloads",
            workloads=[
                "convolution",
                "c2c",
                "r2c",
                "r2r",
            ],
        )
        workload_group(
            "3d_workloads",
            workloads=[
                "c2c",
                "r2c",
                "r2r",
            ],
        )

    workload_variable(
        "fft",
        default="stock",
        values=["cufft", "fftw", "mkl", "onemkl", "rocfft", "stock"],
        strict=True,
        description="FFT library backend",
        workload_group="all_workloads",
    )

    workload_variable(
        "r2r_transform",
        default="cos",
        values=["cos", "sin"],
        strict=True,
        description="R2R transform type",
        workload="r2r",
    )

    workload_variable(
        "precision",
        default="float",
        values=["float", "float-long", "double", "double-long"],
        strict=True,
        description="Precision to use",
        workload_group="all_workloads",
    )

    workload_variable(
        "dim_x",
        default=str(512),
        description="X-dimension of the 3D array",
        workload_group="all_workloads",
    )

    workload_variable(
        "dim_y",
        default=str(512),
        description="Y-dimension of the 3D array",
        workload_group="all_workloads",
    )

    workload_variable(
        "dim_z",
        default=str(512),
        description="Z-dimension of the 3D array",
        workload_group="all_workloads",
    )

    workload_variable(
        "reorder",
        default="reorder",
        values=["reorder", "noreorder"],
        strict=True,
        description="Reorder the 1D array to use contiguous data or not and some data will be strided",
        workload_group="all_workloads",
    )

    workload_variable(
        "reshape",
        default="pencils",
        values=["pencils", "slabs"],
        strict=True,
        description="Use either pencils or slabs reshape logic",
        workload_group="all_workloads",
    )

    workload_variable(
        "comm_method",
        default="a2av",
        values=["a2a", "a2av", "p2p", "p2p_pl"],
        strict=True,
        description="The communication method to use: MPI_Alltoall, MPI_Alltoallv, MPI_Send/MPI_Irecv, or MPI_Isend/MPI_Irecv",
        workload_group="all_workloads",
    )

    workload_variable(
        "num_runs",
        default="5",
        values=["1", "5", "10", "50"],
        strict=True,
        description="Number of times to repeat the run",
        workload_group="all_workloads",
    )

    figure_of_merit(
        "Time per run",
        fom_regex=r"Time per run:\s+(?P<run_time>[0-9]+\.[0-9]+)\s+.*",
        group_name="run_time",
        units="s",
        fom_type=FomType.TIME,
    )

    success_criteria(
        "Time per Run",
        mode="fom_comparison",
        fom_name="Time per run",
        formula="float({value}) > 0.0",
    )

    with when("workload_group=3d_workloads"):
        figure_of_merit(
            "Performance",
            fom_regex=r"Performance:\s+(?P<perf>[0-9]+\.[0-9]+)\s+.*",
            group_name="perf",
            units="GFlops/s",
            fom_type=FomType.THROUGHPUT,
        )

        figure_of_merit(
            "Memory usage per rank",
            fom_regex=r"Memory usage:\s+(?P<mem_use>[0-9]+(\.[0-9]+)?)MB\/rank",
            group_name="mem_use",
            units="MB",
            fom_type=FomType.MEASURE,
        )

        figure_of_merit(
            "Tolerance",
            fom_regex=r"Tolerance:\\s+(?P<tolerance>[0-9]+(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)",
            group_name="tolerance",
            units="",
            fom_type=FomType.INFO,
        )

        figure_of_merit(
            "Maximum error",
            fom_regex=r"Max error:\\s+(?P<error>[0-9]+(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)",
            group_name="error",
            units="",
            fom_type=FomType.INFO,
        )

        success_criteria(
            "Within Tolerance",
            mode="string",
            anti_match=r"^ERROR: observed error after heFFTe benchmark exceeds the tolerance$",
        )
