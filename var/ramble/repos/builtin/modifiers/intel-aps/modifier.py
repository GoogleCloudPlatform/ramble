# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


# Pre-defined charts and graphs
# The per-mode value is a tuple of (options_for_aps, min_stat_level)
_PREDEFINED_REPORTS = {
    "mpi": {
        # rank-to-rank communication time graph, requires APS_STAT_LEVEL >= 4
        "transfer-graph": ("-x --format html", 4),
        # rank-to-rank communication volume graph, requires APS_STAT_LEVEL >= 4
        "transfer-vgraph": ("-x -v --format html", 4),
        # message-size summary, requires APS_STAT_LEVEL >= 2
        "message-sizes": ("-m", 2),
    }
}

_CUSTOM_PREFIX = "custom:"

_REPORT_PREFIX = "aps_report_"


class IntelAps(BasicModifier):
    """Define a modifier for Intel's Application Performance Snapshot

    Intel's Application Performance Snapshot (APS) is a high level profiler. It
    gives a quick view into the high level performance characteristics of an
    experiment. This modifier allows for easy application of APS to experiments.
    """

    name = "intel-aps"

    tags("profiler", "performance-analysis")

    maintainers("douglasjacobsen")

    mode("mpi", description="Mode for collecting mpi statistics")
    default_mode("mpi")

    variable_modification(
        "aps_log_dir",
        "aps_{executable_name}_results_dir",
        method="set",
        modes=["mpi"],
    )
    variable_modification(
        "aps_flags", "-c mpi -r {aps_log_dir}", method="set", modes=["mpi"]
    )
    variable_modification(
        "mpi_command", "aps {aps_flags} ", method="append", modes=["mpi"]
    )

    modifier_variable(
        "aps_stat_level",
        default="1",
        description="Used to define the APS_STAT_LEVEL env variable",
        mode="mpi",
    )

    modifier_variable(
        "aps_extra_reports",
        default="",
        description=f"""
        Comma-separated descriptors specifying extra reports (besides the summary) to generate.
        Syntax definition:
            aps_extra_reports = spec {{ "," spec }}
            spec = pre_defined_spec | custom_spec | "all"
            pre_defined_spec = {",".join(_PREDEFINED_REPORTS["mpi"].keys())}
            custom_spec = "custom" ":" options
            options = <letters>
        Examples:
        * "transfer-graph,message-sizes,custom:-t"
          Generates transfer comm. graph, message-size summary and MPI time per rank chart
        * "all"
          Generates all graphs defined in _PREDEFINED_REPORTS
        """,
        mode="mpi",
    )

    archive_pattern("aps_*_results_dir/*")

    software_spec(
        "intel-oneapi-vtune",
        pkg_spec="intel-oneapi-vtune",
        package_manager="spack*",
    )

    required_package("intel-oneapi-vtune", package_manager="spack*")

    executable_modifier("aps_summary")

    def aps_summary(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_exec = []
        post_exec = []
        if executable.mpi:
            pre_exec.append(
                CommandExecutable(
                    f"load-aps-{executable_name}",
                    template=[
                        "export APS_STAT_LEVEL={aps_stat_level}",
                        "spack load intel-oneapi-vtune",
                        # Clean up previous aps logs to avoid the potential
                        # of out-dated reports.
                        "rm -rf {aps_log_dir}",
                        f"rm -f {{experiment_run_dir}}/{_REPORT_PREFIX}*",
                    ],
                )
            )
            post_exec.append(
                CommandExecutable(
                    f"unload-aps-{executable_name}",
                    template=["spack unload intel-oneapi-vtune"],
                )
            )
            post_exec.append(
                CommandExecutable(
                    f"gen-aps-{executable_name}",
                    template=[
                        'echo "APS Results for executable {executable_name}"',
                        # Prints text summary as well as generating an html report
                        "aps-report -D {aps_log_dir}",
                    ],
                    mpi=False,
                    redirect="{log_file}",
                )
            )

            extra_reports = self.expander.expand_var_name("aps_extra_reports")
            if extra_reports:
                predefined_reports = _PREDEFINED_REPORTS[self._usage_mode]
                specs = [item.strip() for item in extra_reports.split(",")]
                stat_level = self.expander.expand_var_name(
                    "aps_stat_level", typed=True
                )
                cmds = set()

                def _add_cmd(report, opts, min_level=0):
                    if stat_level < min_level:
                        logger.warn(
                            f"Report {report} is skipped as APS_STAT_LEVEL"
                            f" {stat_level} is less than {min_level}"
                        )
                    else:
                        report_path = f'"{{experiment_run_dir}}/{_REPORT_PREFIX}{report}.txt"'
                        cmds.add(
                            f"aps-report {opts} {{aps_log_dir}} > {report_path} 2>&1"
                        )

                for spec in specs:
                    if spec.startswith(_CUSTOM_PREFIX):
                        custom = spec[len(_CUSTOM_PREFIX) :]
                        _add_cmd(
                            f"custom_{custom.replace('-', '').replace(' ', '_')}",
                            custom,
                        )
                    elif spec == "all":
                        for report, (
                            opts,
                            min_level,
                        ) in predefined_reports.items():
                            _add_cmd(report, opts, min_level)
                    else:
                        if spec not in predefined_reports:
                            logger.warn(f"Report {spec} is not defined")
                        else:
                            opts, min_level = predefined_reports[spec]
                            _add_cmd(spec, opts, min_level)

                for i, cmd in enumerate(cmds):
                    post_exec.append(
                        CommandExecutable(
                            f"gen-report{i}",
                            template=cmd,
                            mpi=False,
                            output_capture="",
                            redirect="",
                        )
                    )

        return pre_exec, post_exec

    figure_of_merit_context(
        "APS Executable",
        regex=r"APS Results for executable (?P<exec_name>\w+)",
        output_format="APS on {exec_name}",
    )

    summary_foms = [
        "Application",
        "Report creation date",
        "Number of ranks",
        "Ranks per node",
        "Used statistics",
    ]

    for fom in summary_foms:
        figure_of_merit(
            fom,
            fom_regex=r"\s*" + f"{fom}" + r"\s+:\s+(?P<value>.*)",
            group_name="value",
            units="",
            log_file="{log_file}",
            contexts=["APS Executable"],
        )

    elapsed_time_regex = r"\s*Elapsed Time:\s*(?P<time>[0-9\.]+)"
    figure_of_merit(
        "Elapsed Time",
        fom_regex=elapsed_time_regex,
        group_name="time",
        units="s",
        log_file="{log_file}",
        contexts=["APS Executable"],
    )

    mpi_time_regex = (
        r"\s*MPI Time:\s*(?P<time>[0-9\.]+)\s*s\s*(?P<percent>[0-9\.]+)%.*"
    )
    figure_of_merit(
        "MPI Time",
        fom_regex=mpi_time_regex,
        group_name="time",
        units="s",
        log_file="{log_file}",
        contexts=["APS Executable"],
    )
    figure_of_merit(
        "MPI Percent",
        fom_regex=mpi_time_regex,
        group_name="percent",
        units="%",
        log_file="{log_file}",
        contexts=["APS Executable"],
    )

    mpi_imba_regex = r"\s*MPI Imbalance:\s*(?P<time>[0-9\.]+)\s*s\s*(?P<percent>[0-9\.]+)%.*"
    figure_of_merit(
        "MPI Imbalance Time",
        fom_regex=mpi_imba_regex,
        group_name="time",
        units="s",
        log_file="{log_file}",
        contexts=["APS Executable"],
    )
    figure_of_merit(
        "MPI Imbalance Percent",
        fom_regex=mpi_imba_regex,
        group_name="percent",
        units="%",
        log_file="{log_file}",
        contexts=["APS Executable"],
    )

    disk_io_regex = r"\s*Disk I/O Bound:\s*(?P<time>[0-9\.]+)\s*s\s*(?P<percent>[0-9\.]+)%.*"
    figure_of_merit(
        "Disk I/O Time",
        fom_regex=disk_io_regex,
        group_name="time",
        units="s",
        log_file="{log_file}",
        contexts=["APS Executable"],
    )
    figure_of_merit(
        "Disk I/O Percent",
        fom_regex=disk_io_regex,
        group_name="percent",
        units="%",
        log_file="{log_file}",
        contexts=["APS Executable"],
    )

    mpi_func_regex = r"\s*(?P<func_name>MPI_\S+):\s+(?P<time>[0-9\.]+) s\s+(?P<perc>[0-9\.]+)% of Elapsed Time"
    figure_of_merit(
        "{func_name} Time",
        fom_regex=mpi_func_regex,
        group_name="time",
        units="s",
        log_file="{log_file}",
        contexts=["APS Executable"],
    )
    figure_of_merit(
        "{func_name} Percent",
        fom_regex=mpi_func_regex,
        group_name="perc",
        units="%",
        log_file="{log_file}",
        contexts=["APS Executable"],
    )
