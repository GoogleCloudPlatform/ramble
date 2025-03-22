# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.appkit import *
from ramble.expander import Expander


class Hpcg(ExecutableApplication):
    """The High Performance Conjugate Gradients (HPCG) Benchmark project is an
    effort to create a new metric for ranking HPC systems. HPCG is intended as
    a complement to the High Performance LINPACK (HPL) benchmark, currently
    used to rank the TOP500 computing systems. The computational and data
    access patterns of HPL are still representative of some important scalable
    applications, but not all. HPCG is designed to exercise computational and
    data access patterns that more closely match a different and broad set of
    important applications, and to give incentive to computer system designers
    to invest in capabilities that will have impact on the collective
    performance of these applications."""

    name = "hpcg"

    maintainers("douglasjacobsen")

    tags("benchmark-app", "mini-app", "benchmark")

    executable("execute", "xhpcg", use_mpi=True)

    executable("move-log", "mv HPCG-Benchmark*.txt {out_file}", use_mpi=False)

    workload_group("all_workloads")

    workload_variable(
        "matrix_size",
        default="104 104 104",
        description="Dimensions of the matrix to use",
        workload_group="all_workloads",
    )

    workload_variable(
        "iterations",
        default="60",
        description="Number of iterations to perform",
        workload_group="all_workloads",
    )

    workload_variable(
        "out_file",
        default="{experiment_run_dir}/hpcg_result.out",
        description="Output file for results",
        workload_group="all_workloads",
    )

    out_file = Expander.expansion_str("out_file")

    figure_of_merit(
        "Status",
        log_file=out_file,
        fom_regex=r"Final Summary::HPCG result is (?P<status>[a-zA-Z]+) with a GFLOP/s rating of=(?P<gflops>[0-9\.]+)",
        group_name="status",
        units="",
    )

    figure_of_merit(
        "GFlops",
        log_file=out_file,
        fom_regex=r"Final Summary::HPCG result is (?P<status>[a-zA-Z]+) with a GFLOP/s rating of=(?P<gflops>[0-9\.]+)",
        group_name="gflops",
        units="GFLOP/s",
        fom_type=FomType.THROUGHPUT,
    )

    figure_of_merit(
        "Time",
        log_file=out_file,
        fom_regex=r"Final Summary::Results are.*? execution time.*?is=(?P<exec_time>[0-9\.]*)",
        group_name="exec_time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "ComputeDotProductMsg",
        log_file=out_file,
        fom_regex=r"Final Summary::Reference version of ComputeDotProduct used.*?=(?P<msg>.*)",
        group_name="msg",
        units="",
    )

    figure_of_merit(
        "ComputeSPMVMsg",
        log_file=out_file,
        fom_regex=r"Final Summary::Reference version of ComputeSPMV used.*?=(?P<msg>.*)",
        group_name="msg",
        units="",
    )

    figure_of_merit(
        "ComputeMGMsg",
        log_file=out_file,
        fom_regex=r"Final Summary::Reference version of ComputeMG used.*?=(?P<msg>.*)",
        group_name="msg",
        units="",
    )

    figure_of_merit(
        "ComputeWAXPBYMsg",
        log_file=out_file,
        fom_regex=r"Final Summary::Reference version of ComputeWAXPBY used.*?=(?P<msg>.*)",
        group_name="msg",
        units="",
    )

    figure_of_merit(
        "HPCG 2.4 Rating",
        log_file=out_file,
        fom_regex=r"Final Summary::HPCG 2\.4 rating.*?=(?P<rating>[0-9\.]+)",
        group_name="rating",
        units="",
        fom_type=FomType.THROUGHPUT,
    )

    register_template(
        name="hpcg_dat",
        src_path="hpcg.dat.tpl",
        dest_path="hpcg.dat",
        define_var=False,
    )
