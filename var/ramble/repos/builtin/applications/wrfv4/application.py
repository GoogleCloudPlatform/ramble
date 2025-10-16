# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import shutil

from ramble.appkit import *
from ramble.expander import Expander


class Wrfv4(ExecutableApplication):
    """Define Wrf version 4 application"""

    name = "wrfv4"

    maintainers("douglasjacobsen")

    tags("weather", "nwp", "climate-modeling")

    with when("package_manager_family=spack"):
        define_compiler("gcc9", pkg_spec="gcc@9.3.0")

        software_spec(
            "intel-mpi",
            pkg_spec="intel-oneapi-mpi@2021.13.1",
        )

        software_spec(
            "wrfv4",
            pkg_spec="wrf@4.2 build_type=dm+sm compile_type=em_real nesting=basic ~chem ~pnetcdf",
            compiler="gcc9",
        )

        required_package("wrf")

    variant(
        "wrf_tiles",
        default=False,
        values=[True, False],
        description="Whether to define tiles for WRF or not",
    )

    variant(
        "wrf_explicit_x",
        default=False,
        values=[True, False],
        description="Whether to set explicit nproc_x in the namelist or not",
    )

    variant(
        "wrf_explicit_y",
        default=False,
        values=[True, False],
        description="Whether to set explicit nproc_y in the namelist or not",
    )

    variant(
        "wrf_clean_after_run",
        default=False,
        values=[True, False],
        description="Whether to clean execution artifacts after completion or not",
    )

    input_file(
        "CONUS_2p5km",
        url="https://www2.mmm.ucar.edu/wrf/users/benchmark/v422/v42_bench_conus2.5km.tar.gz",
        sha256="dcae9965d1873c1c1e34e21ad653179783302b9a13528ac10fab092b998578f6",
        description="2.5 km resolution mesh of the continental United States.",
    )

    input_file(
        "CONUS_12km",
        url="https://www2.mmm.ucar.edu/wrf/users/benchmark/v422/v42_bench_conus12km.tar.gz",
        sha256="6a0e87e3401efddc50539e71e5437fd7a5af9228b64cd4837e739737c3706fc3",
        description="12 km resolution mesh of the continental United States.",
    )

    input_file(
        "Maria_1km",
        url="https://www2.mmm.ucar.edu/wrf/users/benchmark/v44/v4.4_bench_maria1km.tar.gz",
        sha256="8a64d45fe53b13a810af8137fab3188c6aad6dc0948e4aa1a84c62bf3afaa102",
        description="1 km Maria workload input",
    )

    executable(
        "cleanup",
        "rm -f rsl.* wrfout*",
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )
    executable(
        "copy",
        template=[
            "cp -R {input_path}/* {experiment_run_dir}/.",
            "ln -s {wrf_path}/run/* {experiment_run_dir}/.",
        ],
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )
    executable(
        "fix_12km",
        template=[
            "sed -i -e 's/ start_hour.*/ start_hour                          = 23,/g' namelist.input",
            "sed -i -e 's/ restart .*/ restart                             = .true.,/g' namelist.input",
        ],
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    executable(
        "define_nproc_x",
        template=[
            "awk '/e_sn.*=/ {print $0 RS \" nproc_x                            = {nproc_x},\"} !/e_sn.*=/ {print $0}' namelist.input > {experiment_run_dir}/temp_namelist.input",
            "mv {experiment_run_dir}/temp_namelist.input {experiment_run_dir}/namelist.input",
        ],
        redirect="",
        output_capture="",
        when="+wrf_explicit_x",
    )

    executable(
        "define_nproc_y",
        template=[
            "awk '/e_sn.*=/ {print $0 RS \" nproc_y                            = {nproc_y},\"} !/e_sn.*=/ {print $0}' namelist.input > {experiment_run_dir}/temp_namelist.input",
            "mv {experiment_run_dir}/temp_namelist.input {experiment_run_dir}/namelist.input",
        ],
        redirect="",
        output_capture="",
        when="+wrf_explicit_y",
    )

    executable("execute", "wrf.exe", use_mpi=True)

    executable(
        "post-exec-clean",
        template=[
            "rm -f {experiment_run_dir}/*.dat ",
            "rm -f {experiment_run_dir}/wrfout*",
            "rm -f {experiment_run_dir}/wrfrst*",
            "rm -f {experiment_run_dir}/wrfinput*",
        ],
        when=["+wrf_clean_after_run"],
    )

    workload(
        "CONUS_2p5km",
        executables=[
            "copy",
            "cleanup",
            "define_nproc_y",
            "define_nproc_x",
            "execute",
            "post-exec-clean",
        ],
        input="CONUS_2p5km",
    )

    workload(
        "CONUS_12km",
        executables=[
            "copy",
            "cleanup",
            "define_nproc_y",
            "define_nproc_x",
            "fix_12km",
            "execute",
            "post-exec-clean",
        ],
        input="CONUS_12km",
    )

    workload(
        "Maria_1km",
        executables=[
            "copy",
            "cleanup",
            "define_nproc_y",
            "define_nproc_x",
            "execute",
            "post-exec-clean",
        ],
        input="Maria_1km",
    )

    workload_group(
        "all_workloads", workloads=["CONUS_2p5km", "CONUS_12km", "Maria_1km"]
    )

    with when("+wrf_tiles"):
        environment_variable(
            "NUM_WRF_TILES",
            value="{num_tiles}",
            description="Number of tiles to use in WRF domain",
            workload_group="all_workloads",
        )

        workload_variable(
            "num_tiles",
            default="1",
            description="Number of tiles to use in WRF domain",
            workload_group="all_workloads",
        )

    workload_variable(
        "nproc_x",
        default="{n_ranks}",
        description="Number of process in the x dimension",
        workload_group="all_workloads",
        when=["+wrf_explicit_x"],
    )

    workload_variable(
        "nproc_y",
        default="{n_ranks}",
        description="Number of process in the y dimension",
        workload_group="all_workloads",
        when=["+wrf_explicit_y", "~wrf_explicit_x"],
    )

    workload_variable(
        "nproc_y",
        default="1",
        description="Number of process in the y dimension",
        workload_group="all_workloads",
        when=["+wrf_explicit_y", "+wrf_explicit_x"],
    )

    workload_variable(
        "input_path",
        description="Path for workload inputs.",
        workload_defaults={
            "CONUS_12km": "{CONUS_12km}",
            "CONUS_2p5km": "{CONUS_2p5km}",
            "Maria_1km": "{Maria_1km}",
        },
    )

    log_str = os.path.join(
        Expander.expansion_str("experiment_run_dir"), "stats.out"
    )

    figure_of_merit(
        "Average Timestep Time",
        log_file=log_str,
        fom_regex=r"Average time:\s+(?P<avg_time>[0-9]+\.[0-9]*)",
        group_name="avg_time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "Cumulative Timestep Time",
        log_file=log_str,
        fom_regex=r"Cumulative time:\s+(?P<total_time>[0-9]+\.[0-9]*)",
        group_name="total_time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "Minimum Timestep Time",
        log_file=log_str,
        fom_regex=r"Min time:\s+(?P<min_time>[0-9]+\.[0-9]*)",
        group_name="min_time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "Maximum Timestep Time",
        log_file=log_str,
        fom_regex=r"Max time:\s+(?P<max_time>[0-9]+\.[0-9]*)",
        group_name="max_time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "Number of timesteps",
        log_file=log_str,
        fom_regex=r"Number of times:\s+(?P<count>[0-9]+)",
        group_name="count",
        units="",
        fom_type=FomType.MEASURE,
    )

    figure_of_merit(
        "Avg. Max Ratio Time",
        log_file=log_str,
        fom_regex=r"Avg time / Max time:\s+(?P<avg_max_ratio>[0-9]+\.[0-9]*)",
        group_name="avg_max_ratio",
        units="",
        fom_type=FomType.MEASURE,
    )

    success_criteria(
        "Complete",
        mode="string",
        match=r".*?wrf: SUCCESS COMPLETE WRF",
        file="{experiment_run_dir}/rsl.out.base",
    )

    archive_pattern("{experiment_run_dir}/rsl.out.*")
    archive_pattern("{experiment_run_dir}/rsl.error.*")

    def _analyze_experiments(self, workspace, app_inst=None):
        import glob
        import re

        experiment_dir = self.expander.expand_var_name("experiment_run_dir")

        # Generate stats file
        file_list = glob.glob(
            os.path.join(
                experiment_dir,
                "rsl.out.*",
            )
        )

        if file_list:
            # Copy first file to rsl.out.base...
            shutil.copyfile(
                file_list[0], os.path.join(experiment_dir, "rsl.out.base")
            )

            timing_regex = re.compile(
                r"Timing for main.*:\s+(?P<main_time>[0-9]+\.[0-9]*).*"
            )
            avg_time = 0.0
            min_time = float("inf")
            max_time = float("-inf")
            sum_time = 0.0
            count = 0
            for out_file in file_list:
                with open(out_file) as f:
                    for line in f.readlines():
                        m = timing_regex.match(line)
                        if m:
                            time = float(m.group("main_time"))
                            count += 1
                            sum_time += time
                            min_time = min(min_time, time)
                            max_time = max(max_time, time)

            avg_time = sum_time / max(count, 1)

            stats_path = os.path.join(
                self.expander.expand_var_name("experiment_run_dir"),
                "stats.out",
            )
            with open(stats_path, "w+") as f:
                f.write("Average time: %s s\n" % (avg_time))
                f.write("Cumulative time: %s s\n" % (sum_time))
                f.write("Min time: %s s\n" % (min_time))
                f.write("Max time: %s s\n" % (max_time))
                f.write(
                    "Avg time / Max time: %s s\n"
                    % (avg_time / max(max_time, float(1.0)))
                )
                f.write("Number of times: %s\n" % (count))

        super()._analyze_experiments(workspace)
