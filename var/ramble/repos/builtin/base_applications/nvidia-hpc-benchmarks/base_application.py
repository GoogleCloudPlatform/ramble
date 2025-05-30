# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.appkit import *


class NvidiaHpcBenchmarks(ExecutableApplication):
    """The NVIDIA HPC-Benchmarks collection provides four benchmarks (HPL,
    HPL-MxP, HPCG, and STREAM) widely used in the HPC community optimized for
    performance on NVIDIA accelerated HPC systems.

    NVIDIA's HPL and HPL-MxP benchmarks provide software packages to solve a
    (random) dense linear system in double precision (64-bit) arithmetic and in
    mixed precision arithmetic using Tensor Cores, respectively, on
    distributed-memory computers equipped with NVIDIA GPUs, based on the Netlib HPL
    benchmark and HPL-MxP benchmark.

    NVIDIA's HPCG benchmark accelerates the High Performance Conjugate Gradients
    (HPCG) Benchmark. HPCG is a software package that performs a fixed number of
    multigrid preconditioned (using a symmetric Gauss-Seidel smoother) conjugate
    gradient (PCG) iterations using double precision (64-bit) floating point
    values.

    NVIDIA's STREAM benchmark is a simple synthetic benchmark program that measures
    sustainable memory bandwidth. NVIDIA HPC-Benchmarks container includes STREAM
    benchmarks optimized for NVIDIA Ampere GPU architecture (sm80), NVIDIA Hopper
    GPU architecture (sm90) and NVIDIA Grace CPU.
    """

    name = "nvidia-hpc-benchmarks"

    maintainers("douglasjacobsen")

    tags("gpu-benchmark", "gpu-accelerated", "nvidia-optimized", "cuda")

    workload_group("all_workloads")

    workload_variable(
        "internal_mpi_command",
        default="",
        description="MPI Command for execution using container built-in MPI",
        workload_group="all_workloads",
    )

    workload_variable(
        "nvshmem_disable_cuda_vmm",
        default="1",
        description="",
        workload_group="all_workloads",
    )
    environment_variable(
        "NVSHMEM_DISABLE_CUDA_VMM",
        "{nvshmem_disable_cuda_vmm}",
        description="",
        workload_group="all_workloads",
    )

    workload_variable(
        "pmix_mca_gds",
        default="^ds12",
        description="",
        workload_group="all_workloads",
    )
    environment_variable(
        "PMIX_MCA_gds",
        "{pmix_mca_gds}",
        description="PMIX MCA gds",
        workload_group="all_workloads",
    )

    workload_variable(
        "ompi_mca_btl",
        default="^vader,tcp,openib,uct",
        description="",
        workload_group="all_workloads",
    )
    environment_variable(
        "OMPI_MCA_btl",
        "{ompi_mca_btl}",
        description="OpenMPI MCA btl",
        workload_group="all_workloads",
    )

    workload_variable(
        "ompi_mca_pml",
        default="ucx",
        description="",
        workload_group="all_workloads",
    )
    environment_variable(
        "OMPI_MCA_pml",
        "{ompi_mca_pml}",
        description="OpenMPI MCA pml",
        workload_group="all_workloads",
    )

    workload_variable(
        "ucx_net_devices",
        default="enp6s0,enp12s0,enp134s0,enp140s0",
        description="",
        workload_group="all_workloads",
    )
    environment_variable(
        "UCX_NET_DEVICES",
        "{ucx_net_devices}",
        description="UCX Net Devices",
        workload_group="all_workloads",
    )

    workload_variable(
        "ucx_max_rndv_rails",
        default="4",
        description="",
        workload_group="all_workloads",
    )
    environment_variable(
        "UCX_MAX_RNDV_RAILS",
        "{ucx_max_rndv_rails}",
        description="UCX MAximum RNDV Rails",
        workload_group="all_workloads",
    )
