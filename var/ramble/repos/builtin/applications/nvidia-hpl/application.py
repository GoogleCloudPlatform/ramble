# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.base_app.builtin.hpl import Hpl as HplBase
from ramble.base_app.builtin.nvidia_hpc_benchmarks import (
    NvidiaHpcBenchmarks as NvidiaHPCBase,
)


class NvidiaHpl(HplBase, NvidiaHPCBase):
    """This application defines how to run NVIDIA's optimized version of HPL,
    which is contained in NVIDIA's HPC-Benchmarks collection.

    The NVIDIA HPC-Benchmarks collection provides four benchmarks (HPL,
    HPL-MxP, HPCG, and STREAM) widely used in the HPC community optimized for
    performance on NVIDIA accelerated HPC systems.

    NVIDIA's HPL and HPL-MxP benchmarks provide software packages to solve a
    (random) dense linear system in double precision (64-bit) arithmetic and in
    mixed precision arithmetic using Tensor Cores, respectively, on
    distributed-memory computers equipped with NVIDIA GPUs, based on the Netlib HPL
    benchmark and HPL-MxP benchmark.

    https://catalog.ngc.nvidia.com/orgs/nvidia/containers/hpc-benchmarks
    """

    name = "nvidia-hpl"

    maintainers("douglasjacobsen")

    tags("benchmark-app", "benchmark", "linpack", "optimized", "nvidia")

    executable(
        "execute",
        "{internal_mpi_command} /workspace/hpl.sh --dat {experiment_run_dir}/HPL.dat",
        use_mpi=True,
    )

    workload("standard", executables=["execute"])
    workload("calculator", executables=["execute"])

    workload_group("standard", workloads=["standard"], mode="append")
    workload_group("calculator", workloads=["calculator"], mode="append")
    workload_group(
        "all_workloads",
        workloads=["standard", "calculator"],
    )

    workload_variable(
        "hpl_fct_comm_policy",
        default="1",
        values=["0", "1"],
        description="Which communication library to use in the panel factorization. 0 = NVSHMEM, 1 = Host MPI",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_FCT_COMM_POLICY",
        "{hpl_fct_comm_policy}",
        description="",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_use_nvshmem",
        default="0",
        values=["0", "1"],
        description="Whether to use NVSHMEM or not. 0 = Disable, 1 = Enable.",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_USE_NVSHMEM",
        "{hpl_use_nvshmem}",
        description="Whether or not to use NVSHMEM",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_p2p_as_bcast",
        default="0",
        values=["0", "1", "2", "3", "4"],
        description="0 = ncclBcast, 1 = ncclSend/Recv, 2 = CUDA-aware MPI, 3 = host MPI, 4 = NVSHMEM",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_P2P_AS_BCAST",
        "{hpl_p2p_as_bcast}",
        description="Which communication library to use in the final solve step.",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_nvshmem_swap",
        default="0",
        values=["0", "1"],
        description="Performs row swaps using NVSHMEM instead of NCCL. 0 = Disable, 1 = Enable.",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_NVSHMEM_SWAP",
        "{hpl_nvshmem_swap}",
        description="Performs row swaps using NVSHMEM instead of NCCL. 0 = Disable, 1 = Enable.",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_chunk_size_nbs",
        default="16",
        description="Number of matrix blocks to group for computations. Needs to be > 0",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_CHUNK_SIZE_NBS",
        "{hpl_chunk_size_nbs}",
        description="Number of matrix blocks to group for computations. Needs to be > 0",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_dist_trsm_flag",
        default="1",
        values=["0", "1"],
        description="Perform the solve step (TRSM) in parallel, rather than on only the ranks that own part of the matrix.",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_DIST_TRSM_FLAG",
        "{hpl_dist_trsm_flag}",
        description="Perform the solve step (TRSM) in parallel, rather than on only the ranks that own part of the matrix.",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_cta_per_fct",
        default="16",
        description="Sets the number of CTAs (thread blocks) for factorization. Needs to be > 0.",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_CTA_PER_FCT",
        "{hpl_cta_per_fct}",
        description="Sets the number of CTAs (thread blocks) for factorization. Needs to be > 0.",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_alloc_hugepages",
        default="0",
        values=["0", "1"],
        description="Use 2MB hugepages for host-side allocations. Done through the madvise syscall.",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_ALLOC_HUGEPAGES",
        "{hpl_alloc_hugepages}",
        description="Use 2MB hugepages for host-side allocations. Done through the madvise syscall.",
        workload_group="all_workloads",
    )

    workload_variable(
        "warmup_end_prog",
        default="5",
        description="Runs the main loop once before the 'real' run. Stops the warmup at x%. Values can be 1 - 100.",
        workload_group="all_workloads",
    )
    environment_variable(
        "WARMUP_END_PROG",
        "{warmup_end_prog}",
        description="Runs the main loop once before the 'real' run. Stops the warmup at x%. Values can be 1 - 100.",
        workload_group="all_workloads",
    )

    workload_variable(
        "test_loops",
        default="1",
        description="Runs the main loop X many times",
        workload_group="all_workloads",
    )
    environment_variable(
        "TEST_LOOPS",
        "{test_loops}",
        description="Runs the main loop X many times",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_cusolver_mp_tests",
        default="1",
        description="Runs several tests of individual components of HPL (GEMMS, comms, etc.)",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_CUSOLVER_MP_TESTS",
        "{hpl_cusolver_mp_tests}",
        description="Runs several tests of individual components of HPL (GEMMS, comms, etc.)",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_cusolver_mp_tests_gemm_iters",
        default="128",
        description="Number of repeat GEMM calls in tests. Needs to be > 0.",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_CUSOLVER_MP_TESTS_GEMM_ITERS",
        "{hpl_cusolver_mp_tests_gemm_iters}",
        description="Number of repeat GEMM calls in tests. Needs to be > 0.",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_ooc_mode",
        default="0",
        description="Enables / disales out-of-core mode",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_OOC_MODE",
        "{hpl_ooc_mode}",
        description="Enables / disales out-of-core mode",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_ooc_max_gpu_mem",
        default="-1",
        description="Limits the amount of GPU memory used for OOC. In GiB. Needs to be >= -1.",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_OOC_MAX_GPU_MEM",
        "{hpl_ooc_max_gpu_mem}",
        description="Limits the amount of GPU memory used for OOC. In GiB. Needs to be >= -1.",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_ooc_tile_m",
        default="4096",
        description="Row blocking factor. Needs to be > 0",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_OOC_TILE_M",
        "{hpl_ooc_tile_m}",
        description="Row blocking factor. Needs to be > 0",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_ooc_tile_n",
        default="4096",
        description="Column blocking factor. Needs to be > 0",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_OOC_TILE_N",
        "{hpl_ooc_tile_n}",
        description="Column blocking factor. Needs to be > 0",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_ooc_num_streams",
        default="3",
        description="Number of streams used for OCC operations",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_OOC_NUM_STREAMS",
        "{hpl_ooc_num_streams}",
        description="Number of streams used for OCC operations",
        workload_group="all_workloads",
    )

    workload_variable(
        "hpl_ooc_safe_size",
        default="2.0",
        description="GPU memory (in GiB) needed for driver. This amount will not be used by HPL OCC",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_OOC_SAFE_SIZE",
        "{hpl_ooc_safe_size}",
        description="GPU memory (in GiB) needed for driver. This amount will not be used by HPL OCC",
        workload_group="all_workloads",
    )

    workload_variable(
        "block_size",
        default="1024",
        description="Size of each block",
        workload_group="calculator",
    )

    figure_of_merit(
        "Per GPU GFlops",
        fom_regex=r".*?\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)"
        + r"\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+"
        + r"(?P<gflops>\S+)\s+\(\s+(?P<per_gpu_gflops>\S+)\)",
        group_name="per_gpu_gflops",
        units="GFLOP/s",
        contexts=["problem-name"],
        fom_type=FomType.THROUGHPUT,
    )
