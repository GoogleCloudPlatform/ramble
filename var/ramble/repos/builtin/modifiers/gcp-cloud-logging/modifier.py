# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403
from ramble.util.shell_utils import last_pid_var


class GcpCloudLogging(BasicModifier):
    """Upload experiment logs to Google Cloud Platform Cloud Logging.

    https://cloud.google.com/logging?e=48754805&hl=en
    """

    name = "gcp-cloud-logging"

    tags("info")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode")

    default_mode("standard")

    target_shells("bash")

    modifier_variable(
        "cloud_logging_tag",
        default="{experiment_namespace}",
        description="Tag to prefix cloud logging entries with",
        modes=["standard"],
    )

    modifier_variable(
        "cloud_logging_status_file",
        default="{experiment_run_dir}/cloud_logging_status",
        description="File to house the status of the cloud logging service",
        modes=["standard"],
    )

    figure_of_merit(
        "Logging service status",
        fom_regex=r"\s*google-cloud-ops-agent\S+ \S+ \S+ (?P<status>\S+)",
        group_name="status",
        units="",
        log_file="{cloud_logging_status_file}",
    )

    register_builtin(
        "start_cloud_logger", required=True, injection_method="prepend"
    )

    def start_cloud_logger(self):
        shell = ramble.config.get("config:shell")
        last_pid_str = last_pid_var(shell)
        return [
            "systemctl list-units google-cloud-ops-agent-fluent* > {cloud_logging_status_file}",
            "tail -f {log_file} | logger -t {cloud_logging_tag} &",
            f"export LOGGER_PID={last_pid_str}",
        ]

    register_builtin(
        "kill_cloud_logger", required=True, injection_method="append"
    )

    def kill_cloud_logger(self):
        return ["kill -9 $LOGGER_PID"]
