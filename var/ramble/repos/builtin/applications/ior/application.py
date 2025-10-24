# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.expander import Expander


class Ior(ExecutableApplication):
    """Define the IOR parallel IO benchmark. Also includes"""

    name = "ior"

    maintainers("rfbgo")

    tags("io-benchmark", "storage-benchmark")

    with when("package_manager_family=spack"):
        define_compiler("gcc", pkg_spec="gcc")
        software_spec("openmpi", pkg_spec="openmpi")
        software_spec("ior", pkg_spec="ior", compiler="gcc")

        required_package("ior")

    workload("multi-file", executables=["ior-prep", "ior"])

    workload("single-file", executables=["ior-prep", "ior"])

    workload_group("all_workloads", workloads=["multi-file", "single-file"])

    workload_variable(
        "transfer-size",
        default="1m",
        description="Transfer Size",
        workload_group="all_workloads",
    )
    workload_variable(
        "block-size",
        default="16m",
        description="Block Size",
        workload_group="all_workloads",
    )
    workload_variable(
        "segment-count",
        default="16",
        description="Segment Count",
        workload_group="all_workloads",
    )
    workload_variable(
        "iterations",
        default="1",
        description="Segment Count",
        workload_group="all_workloads",
    )
    workload_variable(
        "file_args",
        default="-F",
        description="FilePerProc flag",
        workloads=["multi-file"],
    )
    workload_variable(
        "file_args",
        default="",
        description="FilePerProc flag, default to empty",
        workloads=["single-file"],
    )
    workload_variable(
        "target_directory",
        default="{experiment_run_dir}",
        description="Target directory for the r/w test. This can be used to target different file systems.",
        workload_group="all_workloads",
    )
    workload_variable(
        "additional_args",
        default="-C -e",
        description="Additional args to pass. The default aims to suppress the use of page cache.",
        workload_group="all_workloads",
    )

    executable(
        name="ior-prep",
        template="mkdir -p {target_directory}",
        use_mpi=False,
    )

    executable(
        name="ior",
        template="ior -o {target_directory}/testFile -t {transfer-size} -b {block-size} -s {segment-count} -i {iterations} {file_args} {additional_args}",
        use_mpi=True,
    )

    variant(
        "ior_include_iter_foms",
        default=True,
        values=[True, False],
        description="Whether to include per iteration FOMs in analyze",
    )

    # FOMS
    # Match per iteration output in the format:
    # access    bw(MiB/s)  IOPS       Latency(s)  block(KiB) xfer(KiB)  open(s)    wr/rd(s)   close(s)   total(s)   iter
    # ------    ---------  ----       ----------  ---------- ---------  --------   --------   --------   --------   ----
    # write     560.70     2316.04    0.013670    16384      1024.00    0.002069   0.221067   0.693182   0.913139   0
    metrics = [
        "bw",
        "IOPS",
        "latency",
        "block",
        "xfer",
        "open",
        "wrrd",
        "close",
        "total",
        "iter",
    ]
    units = ["MiB/s", "count", "s", "KiB", "KiB", "s", "s", "s", "s", "count"]

    log_str = Expander.expansion_str("log_file")

    with when("+ior_include_iter_foms"):
        iter_regex = ""
        for metric in metrics[0:3]:  # iter is non-float
            iter_regex += (
                r"\s+(?P<" + metric + r">[0-9]+\.[0-9]+)"
            )  # xfer => total
        iter_regex += r"\s+(?P<" + metrics[3] + r">[0-9]+)"  # handle block

        for metric in metrics[4:-1]:  # iter is non-float
            iter_regex += (
                r"\s+(?P<" + metric + r">[0-9]+\.[0-9]+)"
            )  # xfer => total
        iter_regex += r"\s+(?P<" + metrics[-1] + r">[0-9]+)\s*$"  # handle iter

        access_regex = "(?P<access>(read|write))" + iter_regex
        figure_of_merit_context(
            "iter",
            regex=access_regex,
            output_format="{access} iter {iter}",
        )

        # Capture Per Iteration Data
        for metric, unit in zip(metrics, units):
            fom_regex = r"\w+" + iter_regex
            figure_of_merit(
                metric,
                log_file=log_str,
                fom_regex=fom_regex,
                group_name=metric,
                units=unit,
                contexts=["iter"],
            )

    # Capture Summary Data in the format:
    # Operation   Max(MiB)   Min(MiB)  Mean(MiB)     StdDev   Max(OPs)   Min(OPs)  Mean(OPs)     StdDev    Mean(s) Stonewall(s) Stonewall(MiB) Test# #Tasks tPN reps fPP reord reordoff reordrand seed segcnt   blksiz    xsize aggs(MiB)   API RefNum
    # write         612.90     560.70     596.63      14.15     612.90     560.70     596.63      14.15    0.85865         NA            NA     0      2   2   10   0     0        1         0    0     16 16777216  1048576     512.0 POSIX      0
    # Make a tuple of (metric_name, unit, type) to make building the regex easier
    metrics = [
        # ('Operation', '', 'str'),
        ("bw_Max", "MiB", "float"),
        ("bw_Min", "MiB", "float"),
        ("bw_Mean", "MiB", "float"),
        ("bw_StdDev", "", "float"),
        ("ops_Max", "OPs", "float"),
        ("ops_Min", "OPs", "float"),
        ("ops_Mean", "OPs", "float"),
        ("ops_StdDev", "", "float"),
        ("time_Mean", "s", "float"),
        (
            "time_Stonewall",
            "s",
            "str",
        ),  # Currently NA but may one day be a float?
        (
            "bw_Stonewall",
            "MiB",
            "str",
        ),  # Currently NA but may one day be a float?
        ("Test_num", "", "int"),
        ("num_Tasks", "", "int"),
        ("tPN", "", "int"),
        ("reps", "", "int"),
        ("fPP", "", "int"),
        ("reord", "", "int"),
        ("reordoff", "", "int"),
        ("reordrand", "", "int"),
        ("seed", "", "int"),
        ("segcnt", "", "int"),
        ("blksiz", "", "int"),
        ("xsize", "", "int"),
        ("aggs", "MiB", "float"),
        ("API", "", "str"),
        ("RefNum", "", "int"),
    ]

    summary_regex = "(?P<Operation>(read|write))"
    for metric_name, unit, variant in metrics:
        if "str" in variant:
            summary_regex += r"\s+(?P<" + metric_name + r">\w+)"
        elif "int" in variant:
            summary_regex += r"\s+(?P<" + metric_name + r">[0-9]+)"
        elif "float" in variant:
            summary_regex += r"\s+(?P<" + metric_name + r">[0-9]+\.[0-9]+)"
        else:
            logger.error("Incorrect metric for FOMs")

    figure_of_merit_context(
        "summary", regex=summary_regex, output_format="{Operation}"
    )

    for metric, unit, _ in metrics:
        figure_of_merit(
            metric,
            log_file=log_str,
            fom_regex=summary_regex,
            group_name=metric,
            units=unit,
            contexts=["summary"],
        )
