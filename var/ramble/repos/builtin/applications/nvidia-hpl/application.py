# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

from ramble.base_app.builtin.hpl import Hpl as HplBase


class NvidiaHpl(HplBase):
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
        "execute", "./hpl.sh --dat {experiment_run_dir}/HPL.dat", use_mpi=True
    )

    executable(
        "execute-mxp",
        './hpl-mxp.sh --gpu-affinity "{gpu_affinity}" --n {Ns} --nb {block_size} --nprow {Ps} --npcol {Qs} --nporder {nporder}',
        use_mpi=True,
    )

    workload("standard", executables=["execute"])
    workload("calculator", executables=["execute"])

    workload("standard-mxp", executables=["execute-mxp"])
    workload("calculator-mxp", executables=["execute-mxp"])

    workload_group(
        "standard", workloads=["standard", "standard-mxp"], mode="append"
    )
    workload_group(
        "calculator", workloads=["calculator", "calculator-mxp"], mode="append"
    )
    workload_group(
        "all_workloads",
        workloads=["standard", "standard-mxp", "calculator", "calculator-mxp"],
    )
    workload_group("mxp", workloads=["standard-mxp", "calculator-mxp"])

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
        "hpl_fct_comm_policy",
        default="1",
        description="",
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
        description="Whether to use NVSHMEM or not",
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
        description="0 = ncclBcast, 1 = ncclSend/Recv",
        workload_group="all_workloads",
    )
    environment_variable(
        "HPL_P2P_AS_BCAST",
        "{hpl_p2p_as_bcast}",
        description="Whether or not to use P2P for BCAST",
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

    workload_variable(
        "block_size",
        default="1024",
        description="Size of each block",
        workload_group="calculator",
    )

    workload_variable(
        "nporder",
        default="row",
        description="Major order to use for matrix",
        values=["row", "column"],
        workload_group="mxp",
    )

    workload_variable(
        "gpu_affinity",
        default="0:1:2:3:4:5:6:7",
        description="Colon delimited list of GPU IDs",
        workload_group="mxp",
    )
