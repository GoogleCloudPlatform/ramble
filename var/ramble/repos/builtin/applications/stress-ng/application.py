# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class StressNg(ExecutableApplication):
    """Stress-ng is a system stress-testing utility"""

    name = "stress-ng"

    maintainers("robertbird")

    tags("system-utility", "micro-benchmark")

    version("0.12.06", "Version 0.12.06 of stress-ng", preferred=True)

    with when("package_manager_family=spack"):
        define_compiler("gcc", pkg_spec="gcc")

        software_spec(
            "stress-ng-{application::stress-ng::version}",
            pkg_spec="stress-ng@{application::stress-ng::version}",
            compiler="gcc",
        )

        required_package("stress-ng")

    executable(
        "run-stress",
        "{stress_ng_bin} --{stressor} {workers} --timeout {timeout} {extra_args} --metrics-brief",
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    workload("cpu", executable="run-stress")
    workload("matrix", executable="run-stress")
    workload("vecmath", executable="run-stress")

    workload_variable(
        "stress_ng_bin",
        default="stress-ng",
        description="Path to stress-ng binary",
        workloads=["cpu", "matrix", "vecmath"],
    )
    workload_variable(
        "stressor",
        description="Stressor name",
        workload_defaults={
            "cpu": "cpu",
            "matrix": "matrix",
            "vecmath": "vecmath",
        },
    )
    workload_variable(
        "workers",
        default="0",
        description="Number of workers (0 for all)",
        workloads=["cpu", "matrix", "vecmath"],
    )
    workload_variable(
        "timeout",
        default="60s",
        description="Stressor timeout duration",
        workloads=["cpu", "matrix", "vecmath"],
    )
    workload_variable(
        "extra_args",
        description="Extra arguments",
        workload_defaults={
            "cpu": "",
            "matrix": "--matrix-method mult",
            "vecmath": "",
        },
    )
    workload_variable(
        "cpu_list",
        default="",
        description="Taskset core list",
        workloads=["cpu", "matrix", "vecmath"],
    )
    workload_variable(
        "matrix_method",
        default="all",
        description="Matrix method",
        workload="matrix",
    )

    success_criteria(
        "successful_run",
        mode="string",
        match=r"(?s).*successful run completed",
    )

    metrics_regex = (
        r"stress-ng: (info|metrc):\s+\[[0-9]+\]\s+(?P<stressor_name>cpu|matrix|cache|[\w\-]+)\s+"
        + r"(?P<bogo_ops>[0-9]+)\s+(?P<real_time>[0-9\.]+)\s+(?P<usr_time>[0-9\.]+)\s+"
        + r"(?P<sys_time>[0-9\.]+)\s+(?P<bogo_ops_per_s_real>[0-9\.]+)\s+"
        + r"(?P<bogo_ops_per_s_usrsys>[0-9\.]+)"
    )

    figure_of_merit(
        "Bogo Ops",
        fom_regex=metrics_regex,
        group_name="bogo_ops",
        units="",
    )

    figure_of_merit(
        "Bogo Ops/s (Real Time)",
        fom_regex=metrics_regex,
        group_name="bogo_ops_per_s_real",
        units="ops/s",
    )
