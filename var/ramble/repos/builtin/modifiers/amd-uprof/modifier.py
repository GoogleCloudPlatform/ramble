# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class AmdUprof(BasicModifier):
    """Define a modifier for applying AMD uProf profiling."""

    name = "amd-uprof"

    tags("profiler", "performance-analysis")

    maintainers("robertbird")

    mode("mpi", description="Mode for profiling mpi apps")
    mode("standard", description="Mode for profiling serial apps")
    mode(
        "roofline",
        description="Mode for generating roofline using AMDuProfPcm",
    )
    default_mode("mpi")

    modifier_variable(
        "uprof_results_dir",
        default="{experiment_run_dir}/uprof_dir",
        description="Path to store AMD uProf results",
    )

    modifier_variable(
        "uprof_collection_type",
        default="tbp",
        description="Collection type: tbp, ebs, ibs",
    )

    modifier_variable(
        "uprof_args",
        default="collect --config {uprof_collection_type} -o {uprof_results_dir}",
        description="AMD uProf arguments",
    )

    archive_pattern("{uprof_results_dir}/*")

    with when("package_manager_family=spack"):
        software_spec(
            "amduprof",
            pkg_spec="amduprof",
        )

        required_package("amduprof")

    variable_modification(
        "mpi_command",
        "AMDuProfCLI {uprof_args}",
        method="append",
        mode="mpi",
    )

    variable_modification(
        "mpi_command",
        "AMDuProfPcm roofline --msr -O {uprof_results_dir}/roofline.csv --",
        method="prepend",
        mode="roofline",
    )

    executable_modifier("wrap_executable")

    modifier_variable(
        "uprof_report_file",
        default="uprof_report.csv",
        description="File name for uProf report to parse FOMs from",
    )

    figure_of_merit_context(
        "uprof_function",
        regex=r"^\"(?P<func_name>[^\"]+)\",",
        output_format="Function {func_name}",
        log_file="{uprof_report_file}",
    )

    figure_of_merit(
        "CPU Time",
        fom_regex=r"^\"[^\"]+\",(?P<cpu_time>[0-9]+\.[0-9]+),",
        group_name="cpu_time",
        units="s",
        contexts=["uprof_function"],
        log_file="{uprof_report_file}",
    )

    register_builtin(
        "setup_uprof_results_dir", required=True, injection_method="prepend"
    )

    register_builtin(
        "generate_uprof_report", required=True, injection_method="append"
    )

    def setup_uprof_results_dir(self):
        return ["rm -rf {uprof_results_dir} {uprof_report_file}"]

    def wrap_executable(self, executable_name, executable, app_inst=None):
        prepend_execs = []
        append_execs = []

        if self._usage_mode == "standard" and not executable.mpi:
            executable.template = [
                f"AMDuProfCLI {{uprof_args}} {cmd}"
                for cmd in executable.template
            ]

        return prepend_execs, append_execs

    def generate_uprof_report(self):
        if self._usage_mode in ["mpi", "standard"]:
            return [
                "AMDuProfCLI report -i {uprof_results_dir} --report-output {uprof_report_file}"
            ]
        return []
