# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Iozone(ExecutableApplication):
    """Define the Iozone file system benchmark."""

    name = "iozone"

    maintainers("linsword")

    tags("storage-benchmark", "io-benchmark", "filesystem")

    with when("package_manager_family=spack"):
        # gcc >= 10 compilation errors were addressed in https://github.com/spack/spack-packages/pull/2073.
        define_compiler("gcc15", pkg_spec="gcc@15.2.0")
        software_spec("iozone", pkg_spec="iozone@3_506", compiler="gcc15")
        required_package("iozone")

    register_template(
        "generate_clientlist",
        src_path="generate_clientlist.sh.tpl",
        dest_path="generate_clientlist.sh",
    )

    # The purpose of this step is to generate client entries expected by iozone.
    # For instance, if running on two nodes, with PPN=3, then the clientlist
    # file should look like the following:
    #   client1 /path/to/working_directory/ /path/to/iozone
    #   client1 /path/to/working_directory/ /path/to/iozone
    #   client1 /path/to/working_directory/ /path/to/iozone
    #   client2 /path/to/working_directory/ /path/to/iozone
    #   client2 /path/to/working_directory/ /path/to/iozone
    #   client2 /path/to/working_directory/ /path/to/iozone
    # The number of clientlist entries needs to match with the `-t` option.
    executable(
        "gen_clientlist",
        template="bash generate_clientlist.sh",
        use_mpi=False,
    )

    executable(
        "execute",
        template="{iozone_bin_path} {test_args} -r {record_size} -s {file_size} -t {n_ranks} -+m {clientlist_path} {additional_args}",
        use_mpi=False,
    )

    workload("cluster", executables=["gen_clientlist", "execute"])

    workload_variable(
        "test_args",
        default="-i 0 -i 1",
        description="Specify the tests to run",
        workload="cluster",
    )

    workload_variable(
        "file_size",
        default="16g",
        description="Size of the test file",
        workload="cluster",
    )

    workload_variable(
        "record_size",
        default="1m",
        description="Record size",
        workload="cluster",
    )

    workload_variable(
        "working_directory",
        default="{experiment_run_dir}",
        description="Working directory for the test",
        workload="cluster",
    )

    workload_variable(
        "additional_args", default="-c -e -+n -I", workload="cluster"
    )

    workload_variable(
        "rsh_alternative",
        default="ssh",
        description="Alternative remote access mechanism of rsh",
        workload="cluster",
        # iozone.c uses `getenv("RSH")` to decide on its remote access mechanism
        env_var_name="RSH",
    )

    workload_variable(
        "hostfile_path",
        default="{experiment_run_dir}/hostfile",
        workload="cluster",
    )

    workload_variable(
        "clientlist_path",
        default="{experiment_run_dir}/clientlist",
        workload="cluster",
    )

    workload_variable(
        "iozone_bin_path",
        default="{iozone_path}/bin/iozone",
        workload="cluster",
    )

    throughput_regex = r"\s*Children see throughput for\s+\d+\s+(?P<test>.*?)\s*=\s*(?P<throughput>[\d.]+)"

    figure_of_merit_context(
        "test", regex=throughput_regex, output_format="Test {test}"
    )

    figure_of_merit(
        "Total throughput",
        fom_regex=throughput_regex,
        group_name="throughput",
        units="kB/sec",
        contexts=["test"],
    )

    for fom in ("Min", "Max", "Avg"):
        figure_of_merit(
            f"{fom} throughput",
            fom_regex=rf"\s*{fom} throughput per process\s*=\s*(?P<throughput>[\d.]+)",
            group_name="throughput",
            units="kB/sec",
            contexts=["test"],
        )

    success_criteria(
        "test_complete",
        mode="string",
        match=r".*?iozone test complete",
    )
