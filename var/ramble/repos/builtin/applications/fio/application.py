# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.appkit import *

from spack.util.path import canonicalize_path


class Fio(ExecutableApplication):
    """Flexible I/O Tester. Fio spawns a number of threads or processes doing a
    particular type of I/O action as specified by the user. fio takes a number
    of global parameters, each inherited by the thread unless otherwise
    parameters given to them overriding that setting is given.
    """

    name = "fio"

    maintainers("dapomeroy")

    tags("io-benchmark", "storage-benchmark")

    with when("package_manager_family=spack"):
        define_compiler("gcc13", pkg_spec="gcc@13.1.0")

        software_spec("fio", pkg_spec="fio@3.37 +libaio")

    executable(
        "run",
        template=[
            "echo 'Running job file {job_file}...'",
            "fio --output={out_file} --output-format {out_format} --eta=never {job_file_path}",
        ],
        use_mpi=False,
    )

    # Use client/server mode to run on multiple nodes
    executable(
        "slurm-multinode-run",
        template=[
            "export DIRECTORY='{directory}'",
            "echo 'Starting fio servers...'",
            "pdsh -w $SLURM_JOB_NODELIST {experiment_run_dir}/fio_start_server.sh",
            "echo 'Creating test directory $DIRECTORY...'",
            "mkdir -p '$DIRECTORY'",
            "echo 'Running job file {job_file} on nodes: $SLURM_JOB_NODELIST'",
            "fio --output={out_file} --output-format {out_format} --eta=never --client=hostfile {job_file_path}",
            "echo 'Fio jobs finished.'",
            "echo 'Stopping fio servers...'",
            "pdsh -w $SLURM_JOB_NODELIST {experiment_run_dir}/fio_stop_server.sh",
        ],
        use_mpi=False,
    )

    executable(
        "cleanup",
        template=[
            "echo 'Deleting temporary files'",
            "rm -f {directory}/*{experiment_name}.[0-9]*",
        ],
        use_mpi=False,
    )

    workload("standard", executables=["run", "cleanup"])
    workload("slurm-multinode", executables=["slurm-multinode-run", "cleanup"])
    all_workloads = ["standard", "slurm-multinode"]

    workload_variable(
        "job_file",
        description="Job file to run. If a job file is not specified, one will be generated from variables.",
        default="generated.conf",
        workloads=all_workloads,
    )
    workload_variable(
        "job_file_path",
        description=("Path to job file."),
        default="{experiment_run_dir}/{job_file}",
        workloads=all_workloads,
    )
    workload_variable(
        "out_file",
        description="File to write results",
        default="fio.out",
        workloads=all_workloads,
    )
    workload_variable(
        "out_format",
        description="Format to write results. Defaults to 'json' for Ramble to analyze results.",
        default="json",
        workloads=all_workloads,
    )
    workload_variable(
        "job_name",
        description="Job name",
        default="{experiment_name}",
        workloads=all_workloads,
    )
    workload_variable(
        "directory",
        description="Used to place files in a different location than ./",
        default="{experiment_run_dir}",
        workloads=all_workloads,
    )

    # variables set using strings / numbers stored as strings
    _STR_VARS = {
        "ioengine",
        "runtime",
        "size",
        "rw",
        "bs",
        "iodepth",
        "numjobs",
        "directory",
    }

    # variables that are set using boolean value (var=0|1)
    _BOOL_VARS = {
        "buffered",
        "direct",
        "randrepeat",
    }

    # variables that are set using the var name, defaults to unset
    _SET_VARS = {
        "group_reporting",
        "norandommap",
        "refill_buffers",
        "time_based",
        "stonewall",
    }

    # If not set in Ramble, workload vars are not written to job file / use fio application default
    workload_variable(
        "ioengine",
        description="I/O engine",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "direct",
        description="If true, use non-buffered I/O",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "buffered",
        description="If true, use buffered I/O. This is the opposite of the direct option",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "time_based",
        description="If set, fio will run for the duration of the runtime specified even if the file(s) are completely read or written.",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "runtime",
        description="Limit runtime. The test will run until it completes the configured I/O workload or until it has run for this specified amount of time, whichever occurs first.",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "refill_buffers",
        description="If this option is given, fio will refill the I/O buffers on every submit. ",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "norandommap",
        description="Normally fio will cover every block of the file when doing random I/O. If this option is given, fio will just get a new random offset without looking at past I/O history.",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "randrepeat",
        description="Seed all random number generators in a predictable way so the pattern is repeatable across runs. ",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "group_reporting",
        description="To see the final report per-group instead of per-job, use group_reporting. Jobs in a file will be part of the same reporting group, unless if separated by a stonewall, or by using new_group.",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "size",
        description="The total size of file I/O for each thread of this job.",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "rw",
        description="Type of I/O pattern",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "bs",
        description="The block size in bytes used for I/O units.",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "iodepth",
        description="Number of I/O units to keep in flight against the file.",
        default=None,
        workloads=all_workloads,
    )
    workload_variable(
        "numjobs",
        description="Create the specified number of clones of this job.",
        default=None,
        workloads=all_workloads,
    )

    log_str = os.path.join("{experiment_run_dir}", "metrics.out")

    # Job-level FOMs
    figure_of_merit(
        "Job Name",
        log_file=log_str,
        fom_regex=r"jobname: (?P<jobname>\S+)",
        group_name="jobname",
        units="",
    )
    figure_of_merit(
        "Job Runtime",
        log_file=log_str,
        fom_regex=r"job_runtime: (?P<job_runtime>[0-9]+)",
        group_name="job_runtime",
        units="msec",
    )
    figure_of_merit(
        "CPU Usage (User)",
        log_file=log_str,
        fom_regex=r"usr_cpu: (?P<usr_cpu>[0-9\.]+)",
        group_name="usr_cpu",
        units="",
    )
    figure_of_merit(
        "CPU Usage (System)",
        log_file=log_str,
        fom_regex=r"sys_cpu: (?P<sys_cpu>[0-9\.]+)",
        group_name="sys_cpu",
        units="",
    )
    figure_of_merit(
        "Context Switches",
        log_file=log_str,
        fom_regex=r"ctx: (?P<ctx>[0-9]+)",
        group_name="ctx",
        units="",
    )
    figure_of_merit(
        "Major Faults",
        log_file=log_str,
        fom_regex=r"majf: (?P<majf>[0-9]+)",
        group_name="majf",
        units="",
    )
    figure_of_merit(
        "Minor Faults",
        log_file=log_str,
        fom_regex=r"minf: (?P<minf>[0-9]+)",
        group_name="minf",
        units="",
    )
    figure_of_merit(
        "FIO Version",
        log_file=log_str,
        fom_regex=r"fio version: (?P<fio_version>\S+)",
        group_name="fio_version",
        units="",
    )

    # Shared FOMs for read, write, trim contexts
    shared_fom_parts_1 = [
        ("io_bytes", r"[0-9]+"),
        ("io_kbytes", r"[0-9]+"),
        ("bw_bytes", r"[0-9]+"),
        ("bw", r"[0-9]+"),
        ("iops", r"[0-9\.]+"),
        ("runtime", r"[0-9]+"),
        ("total_ios", r"[0-9]+"),
        ("short_ios", r"[0-9]+"),
        ("drop_ios", r"[0-9]+"),
    ]

    shared_fom_parts_2 = [
        ("slat_min", r"[0-9]+", "slat_min_unit", r"[mnus]+"),
        ("slat_max", r"[0-9]+", "slat_max_unit", r"[mnus]+"),
        ("slat_mean", r"[0-9\.]+", "slat_mean_unit", r"[mnus]+"),
        ("slat_stddev", r"[0-9\.]+", "slat_stddev_unit", r"[mnus]+"),
        ("slat_N", r"[0-9]+", "slat_N_unit", ""),
        ("clat_min", r"[0-9]+", "clat_min_unit", r"[mnus]+"),
        ("clat_max", r"[0-9]+", "clat_max_unit", r"[mnus]+"),
        ("clat_mean", r"[0-9\.]+", "clat_mean_unit", r"[mnus]+"),
        ("clat_stddev", r"[0-9\.]+", "clat_stddev_unit", r"[mnus]+"),
        ("clat_N", r"[0-9]+", "clat_N_unit", ""),
        ("lat_min", r"[0-9]+", "lat_min_unit", r"[mnus]+"),
        ("lat_max", r"[0-9]+", "lat_max_unit", r"[mnus]+"),
        ("lat_mean", r"[0-9\.]+", "lat_mean_unit", r"[mnus]+"),
        ("lat_stddev", r"[0-9\.]+", "lat_stddev_unit", r"[mnus]+"),
        ("lat_N", r"[0-9]+", "lat_N_unit", ""),
    ]

    shared_fom_parts_3 = [
        ("bw_min", r"[0-9]+"),
        ("bw_max", r"[0-9]+"),
        ("bw_agg", r"[0-9\.]+"),
        ("bw_mean", r"[0-9\.]+"),
        ("bw_dev", r"[0-9\.]+"),
        ("bw_samples", r"[0-9]+"),
        ("iops_min", r"[0-9]+"),
        ("iops_max", r"[0-9]+"),
        ("iops_mean", r"[0-9\.]+"),
        ("iops_stddev", r"[0-9\.]+"),
        ("iops_samples", r"[0-9]+"),
    ]

    shared_fom_regex = ""
    for fom_name, fom_part_regex in shared_fom_parts_1:
        shared_fom_regex += (
            rf"\s*{fom_name}:\s+(?P<{fom_name}>{fom_part_regex}),*"
        )
    for fom_name, fom_part_regex, unit_name, unit_regex in shared_fom_parts_2:
        shared_fom_regex += (
            rf"\s*{fom_name}:\s+(?P<{fom_name}>{fom_part_regex})"
        )
        if unit_regex:
            shared_fom_regex += rf"(?P<{unit_name}>{unit_regex})?"
        shared_fom_regex += r",*"
    for fom_name, fom_part_regex in shared_fom_parts_3:
        shared_fom_regex += (
            rf"\s*{fom_name}:\s+(?P<{fom_name}>{fom_part_regex}),*"
        )

    shared_fom_defs = [
        ("Total I/O (Bytes)", "io_bytes", "B"),
        ("Total I/O", "io_kbytes", "KiB"),
        ("Bandwidth B/sec", "bw_bytes", "B/sec"),
        ("Bandwidth", "bw", "KiB/sec"),
        ("IOPS", "iops", ""),
        ("Runtime", "runtime", "msec"),
        ("Total I/Os", "total_ios", ""),
        ("Short I/Os", "short_ios", ""),
        ("Dropped I/Os", "drop_ios", ""),
        ("Submission Latency (Min)", "slat_min", "{slat_min_unit}"),
        ("Submission Latency (Max)", "slat_max", "{slat_max_unit}"),
        ("Submission Latency (Mean)", "slat_mean", "{slat_mean_unit}"),
        ("Submission Latency (StdDev)", "slat_stddev", "{slat_stddev_unit}"),
        ("Submission Latency (N)", "slat_N", ""),
        ("Completion Latency (Min)", "clat_min", "{clat_min_unit}"),
        ("Completion Latency (Max)", "clat_max", "{clat_max_unit}"),
        ("Completion Latency (Mean)", "clat_mean", "{clat_mean_unit}"),
        ("Completion Latency (StdDev)", "clat_stddev", "{clat_stddev_unit}"),
        ("Completion Latency (N)", "clat_N", ""),
        ("Total Latency (Min)", "lat_min", "{lat_min_unit}"),
        ("Total Latency (Max)", "lat_max", "{lat_max_unit}"),
        ("Total Latency (Mean)", "lat_mean", "{lat_mean_unit}"),
        ("Total Latency (StdDev)", "lat_stddev", "{lat_stddev_unit}"),
        ("Total Latency (N)", "lat_N", ""),
        ("Bandwidth (Min)", "bw_min", ""),
        ("Bandwidth (Max)", "bw_max", ""),
        ("Bandwidth (Aggregate % of Total)", "bw_agg", ""),
        ("Bandwidth (Mean)", "bw_mean", ""),
        ("Bandwidth (StdDev)", "bw_dev", ""),
        ("Bandwidth (N Samples)", "bw_samples", ""),
        ("IOPS (Min)", "iops_min", ""),
        ("IOPS (Max)", "iops_max", ""),
        ("IOPS (Mean)", "iops_mean", ""),
        ("IOPS (StdDev)", "iops_stddev", ""),
        ("IOPS (N Samples)", "iops_samples", ""),
    ]

    for ctx in ["read", "write", "trim"]:
        context_regex = rf"{ctx}:" + shared_fom_regex
        figure_of_merit_context(
            f"{ctx}", regex=context_regex, output_format=f"{ctx}"
        )
        for fom_def in shared_fom_defs:
            figure_of_merit(
                fom_def[0],
                log_file=log_str,
                fom_regex=context_regex,
                group_name=f"{fom_def[1]}",
                units=f"{fom_def[2]}",
                contexts=[f"{ctx}"],
            )

    register_template(
        "fio_start_server",
        src_path="fio_start_server.sh.tpl",
        dest_path="fio_start_server.sh",
        extra_vars_func="software_env_cmds",
    )

    def _software_env_cmds(self):
        env_commands = ""
        if self.package_manager:
            env_commands = self.package_manager.environment_load_commands()
        if isinstance(env_commands, list):
            env_commands = "\n".join(env_commands)

        return {"load_software_env": env_commands}

    register_template(
        "fio_stop_server",
        src_path="fio_stop_server.sh.tpl",
        dest_path="fio_stop_server.sh",
    )

    register_phase(
        "write_jobfile", pipeline="setup", run_after=["make_experiments"]
    )

    def _write_jobfile(self, workspace, app_inst):
        """Writes a job file if one is not specified"""
        job_file = self.expander.expand_var_name("job_file")
        if job_file != "generated.conf":
            return

        jobfile_path = get_file_path(
            canonicalize_path(
                os.path.join(
                    self.expander.expand_var_name("experiment_run_dir"),
                    job_file,
                )
            ),
            workspace,
        )

        with open(jobfile_path, "w+") as f:
            f.write(
                "[" + self.expander.expand_var_name("experiment_name") + "]\n"
            )
            for str_var in self._STR_VARS:
                str_val = self.expander.expand_var_name(str_var)
                if str_val != "None":
                    f.write(f"{str_var}={str_val}\n")

            for bool_var in self._BOOL_VARS:
                bool_val = self.expander.expand_var_name(bool_var, typed=True)
                if bool_val != "None":
                    # FIO takes bool as int
                    if bool(bool_val) is True:
                        bool_val = 1
                    else:
                        bool_val = 0
                    f.write(f"{bool_var}={bool_val}\n")

            for set_var in self._SET_VARS:
                set_val = self.expander.expand_var_name(set_var, typed=True)
                if set_val != "None":
                    f.write(f"{set_var}\n")

    def _prepare_analysis(self, workspace, app_inst):
        """Reads JSON metrics from fio.out and formats them in a new file
        to be processed by Ramble.

        FIO outputs a single JSON with a list of all jobs in the job file. Each
        job has nested dicts up to 4 levels deep. Since Ramble only supports a
        single level of contexts, these levels have been flattened and Ramble
        generates one job per experiment/job file.

        For standard workloads, a single job output is generated. For
        clint/server multinode workloads, Ramble uses the summary of all
        clients.
        """
        import json

        def _split_unit(in_str):
            if "_ns" in in_str or "_us" in in_str or "_ms" in in_str:
                metric, unit = in_str.split("_")
            else:
                metric, unit = in_str, ""
            return metric, unit

        fio_outfile = get_file_path(
            canonicalize_path(
                os.path.join(
                    app_inst.expander.experiment_run_dir,
                    app_inst.expander.expand_var_name("out_file"),
                )
            ),
            workspace,
        )

        if not os.path.exists(fio_outfile):
            return

        formatted_metrics = []

        with open(fio_outfile) as f:
            file = ""
            # ignore client/server output headers that begin with <server-hostname>
            for line in f:
                if line.startswith("<"):
                    continue
                else:
                    file += line

            try:
                metrics_dict = json.loads(file)

                data_key = "jobs"
                # client/server mode outputs data with a different key
                if "client_stats" in metrics_dict:
                    data_key = "client_stats"

                # for standard mode using generated conf, there should be one job in dict["jobs"]
                # for client/server mode, if run on a single node/server there will be one job in
                # dict["client_stats"]. If run on n>1 nodes/servers, output is n jobs and 1 summary
                if len(metrics_dict[data_key]) == 1:
                    job = metrics_dict[data_key][0]
                elif (
                    len(metrics_dict[data_key]) > 1
                    and data_key == "client_stats"
                ):
                    for j in metrics_dict[data_key]:
                        # When summary exists, skip individual jobs
                        if j["jobname"] != "All clients":
                            continue
                        else:
                            job = j
                else:
                    logger.warn(
                        "Found more than one job result in experiment output."
                    )

                # first level: job-level data, read/write dicts, depth/latency dicts, etc
                for key, val in job.items():
                    if isinstance(val, dict):
                        context_metrics = []

                        # second level: read/write data, depth/latencty stats, statistical dicts
                        for key2, val2 in val.items():
                            if isinstance(val2, dict):
                                key2, unit = _split_unit(key2)

                                # third level: contains values and percentile dict, flatten with l2
                                for key3, val3 in val2.items():
                                    # todo: if percentile data is useful, flatten and add FOM(s)
                                    if key3 == "percentile":
                                        continue

                                    if key3 == "N":
                                        unit = ""

                                    # slat, clat, and lat will be one of 3 units (_ns, _us, or _ms)
                                    context_metrics.append(
                                        f"{key2}_{key3}: {val3}{unit}"
                                    )
                            else:
                                context_metrics.append(f"{key2}: {val2}")

                        context_out = f"{key}: " + ", ".join(context_metrics)
                        formatted_metrics.append(context_out)
                    else:
                        formatted_metrics.append(f"{key}: {val}")

                formatted_metrics.append(
                    f"fio version: {metrics_dict['fio version']}"
                )

            except Exception as e:
                logger.warn(f"Error reading metrics data: {e}")

            metrics_outfile_path = os.path.join(
                app_inst.expander.experiment_run_dir, "metrics.out"
            )

            with open(metrics_outfile_path, "w") as metrics_out:
                for line in formatted_metrics:
                    metrics_out.write(line + "\n")
