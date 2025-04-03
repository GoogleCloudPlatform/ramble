# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.appkit import *


class NcclTests(ExecutableApplication):
    """These tests check both the performance and the correctness of NCCL
    operations.

    https://github.com/NVIDIA/nccl-tests
    """

    name = "nccl-tests"
    maintainers("douglasjacobsen")

    tags("gpu")

    executable(
        "all-to-all-execute",
        template=["alltoall_perf {additional_args}"],
        use_mpi=True,
    )
    workload("all-to-all", executables=["all-to-all-execute"])

    executable(
        "all-reduce-execute",
        template=["all_reduce_perf {additional_args}"],
        use_mpi=True,
    )
    workload("all-reduce", executables=["all-reduce-execute"])

    executable(
        "all-gather-execute",
        template=["all_gather_perf {additional_args}"],
        use_mpi=True,
    )
    workload("all-gather", executables=["all-gather-execute"])

    executable(
        "reduce-scatter-execute",
        template=["reduce_scatter_perf {additional_args}"],
        use_mpi=True,
    )
    workload("reduce-scatter", executables=["reduce-scatter-execute"])

    executable(
        "send-recv-execute",
        template=["sendrecv_perf {additional_args}"],
        use_mpi=True,
    )
    workload("send-recv", executables=["send-recv-execute"])

    all_workloads = [
        "all-reduce",
        "all-to-all",
        "all-gather",
        "reduce-scatter",
        "send-recv",
    ]

    software_spec(
        "nccl-test",
        pkg_spec="nccl-tests",
        when=["package_manager_family=spack"],
    )
    required_package("nccl-tests", when=["package_manager_family=spack"])

    workload_variable(
        "num_gpus_per_task",
        default="1",
        description="Number of GPUs per task",
        workloads=all_workloads,
    )
    workload_variable(
        "begin_message_size",
        default="8",
        description="Beginning message size",
        workloads=all_workloads,
    )
    workload_variable(
        "end_message_size",
        default="8G",
        description="Ending message size",
        workloads=all_workloads,
    )
    workload_variable(
        "message_size_factor",
        default="2",
        description="Factor used in size sweep",
        workloads=all_workloads,
    )
    workload_variable(
        "begin_message_size",
        default="8",
        description="Beginning message size",
        workloads=all_workloads,
    )
    workload_variable(
        "warmup_iters",
        default="5",
        description="Number of warmup iterations",
        workloads=all_workloads,
    )
    workload_variable(
        "num_iters",
        default="100",
        description="Number of iterations to perform",
        workloads=all_workloads,
    )
    workload_variable(
        "result_check",
        default="1",
        description="0 to skip checking, 1 to enable checking",
        workloads=all_workloads,
    )

    workload_variable(
        "additional_args",
        default="-b {begin_message_size} -e {end_message_size} -f {message_size_factor} -g {num_gpus_per_task} -w {warmup_iters} --iters {num_iters} -c {result_check}",
        description="Arguments for all reduce",
        workloads=all_workloads,
    )

    workload_variable(
        "nccl_tests_split_mask",
        default="",
        description='How NCCL communicators should be split, if at all. "0x7" for rail-aligned, "0x0" for world-level.',
        workloads=all_workloads,
        expandable=False,
    )

    environment_variable(
        "NCCL_TESTS_SPLIT_MASK",
        "{nccl_tests_split_mask}",
        'How NCCL communicators should be split, if at all. "0x7" for rail-aligned, "0x0" for world-level.',
        workloads=all_workloads,
    )

    # (output_name, units, group_name, regex)
    regex_parts = [
        ("Size", "B", "size", "[0-9]+"),
        ("Count", "elements", "count", "[0-9]+"),
        ("Type", "", "type", r"\S+"),
        ("Reduction Operator", "", "redop", r"\S+"),
        ("Root", "", "root", r"\S+"),
        ("Out of Place Time", "us", "ooptime", r"[0-9]+\.?[0-9]+"),
        ("Out of Place Alg Bandwidth", "GB/s", "oopalgbw", r"[0-9]+\.?[0-9]+"),
        ("Out of Place Bus Bandwidth", "GB/s", "oopbusbw", r"[0-9]+\.?[0-9]+"),
        ("Out of Place Number Wrong", "", "oopnumwrong", r"\S+"),
        ("In Place Time", "us", "iptime", r"[0-9]+\.?[0-9]+"),
        ("In Place Alg Bandwidth", "GB/s", "ipalgbw", r"[0-9]+\.?[0-9]+"),
        ("In Place Bus Bandwidth", "GB/s", "ipbusbw", r"[0-9]+\.?[0-9]+"),
        ("In Place Number Wrong", "", "ipnumwrong", r"\S+"),
    ]

    fom_regex = ""
    for regex_part in regex_parts:
        fom_regex += rf"\s+(?P<{regex_part[2]}>{regex_part[3]})"

    figure_of_merit_context("size", output_format="{size}", regex=fom_regex)
    for regex_part in regex_parts:
        figure_of_merit(
            regex_part[0],
            fom_regex=fom_regex,
            units=regex_part[1],
            group_name=regex_part[2],
            contexts=["size"],
        )

    figure_of_merit(
        "Avg. Bus Bandwidth",
        fom_regex=r"\s*Avg bus bandwidth\s+:\s+(?P<bw>[0-9]+\.?[0-9]+)",
        group_name="bw",
        units="GB/s",
    )
    figure_of_merit(
        "Out of bounds values",
        fom_regex=r"\s*Out of bounds values\s*:\s+(?P<count>[0-9]+)",
        group_name="count",
        units="",
    )
