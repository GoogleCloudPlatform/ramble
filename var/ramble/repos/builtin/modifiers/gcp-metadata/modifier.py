# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class GcpMetadata(BasicModifier):
    """Define a modifier to grab GCP VM metadata

    This mod can capture useful metadata (such as node type and VM image) for
    GCP VMs

    Requires a definition for the `hostlist` variable, to be able to capture
    per-node metadata.
    """

    name = "GcpMetadata"

    tags("gcp-metadata")
    maintainers("rfbgo")

    mode("standard", description="Standard execution mode")
    default_mode("standard")

    software_spec("pdsh", pkg_spec="pdsh", package_manager="spack*")

    required_variable("hostlist")

    executable_modifier("gcp_metadata_exec")

    def gcp_metadata_exec(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        if hasattr(self, "_already_applied"):
            return [], []

        self._already_applied = True

        post_cmds = []
        pre_cmds = []

        pre_cmds.append(
            CommandExecutable(
                "save-old-loglevel",
                template=[
                    'old_pdsh_args="$PDSH_SSH_ARGS_APPEND"',
                    'export PDSH_SSH_ARGS_APPEND="-q"',
                ],
            )
        )

        payloads = [
            # type, end point, per_node
            ("instance", "machine-type", False),
            ("instance", "image", False),
            ("instance", "hostname", False),
            (
                "instance",
                "id",
                True,
            ),  # True since we want the gid of every node
            ("project", "numeric-project-id", False),
            ("instance", "attributes/physical_host", True),
        ]

        for type, end_point, per_node in payloads:
            prefix = ""
            suffix = ""
            if per_node:
                prefix = "pdsh -N -w {hostlist} '"
                suffix = "'"
            log_name = end_point.split("/")[-1]
            pre_cmds.append(
                CommandExecutable(
                    "machine-type",
                    template=[
                        # Fail silently (-f) to avoid jamming the log (say with 404 html)
                        # This is especially pertinent to /attribute/physical_host,
                        # which is only available for VMs with placement policy.
                        f'{prefix} curl -s -f -w "\\n" "http://metadata.google.internal/computeMetadata/v1/{type}/{end_point}" -H "Metadata-Flavor: Google" {suffix}'
                    ],
                    mpi=False,
                    redirect=f"{{experiment_run_dir}}/gcp-metadata.{log_name}.log",
                    output_capture=">",
                )
            )

        pre_cmds.append(
            CommandExecutable(
                "restore-old-loglevel",
                template=['export PDSH_SSH_ARGS_APPEND="$old_pdsh_args"'],
            )
        )

        return pre_cmds, post_cmds

    def _process_id_list(self):
        import os.path

        ids = set()
        file_name = self.expander.expand_var(
            "{experiment_run_dir}/gcp-metadata.id.log"
        )

        if os.path.isfile(file_name):
            with open(file_name) as f:
                for cur_id in f.readlines():
                    cur_id = cur_id.strip()
                    if cur_id.isnumeric():
                        ids.add(cur_id)

            with open(
                self.expander.expand_var(
                    "{experiment_run_dir}/gcp-metadata.id_list.log"
                ),
                "w+",
            ) as f:
                f.write(", ".join(sorted(ids)))

    def _process_physical_hosts(self):
        level0_groups = set()
        level1_groups = set()
        level2_groups = set()
        all_hosts = set()

        with open(
            self.expander.expand_var(
                "{experiment_run_dir}/gcp-metadata.physical_host.log"
            )
        ) as f:
            for raw_host in f.readlines():
                physical_host = raw_host[1:].strip()
                tty.debug(f"  Host line: {physical_host}")
                all_hosts.add(physical_host)
                levels = physical_host.split("/")
                tty.debug(f"   Levels: {levels}")
                if len(levels) == 3:
                    level0_groups.add(levels[0])
                    level1_groups.add(levels[1])
                    level2_groups.add(levels[2])

        with open(
            self.expander.expand_var(
                "{experiment_run_dir}/gcp-metadata.topology_summary.log"
            ),
            "w+",
        ) as f:
            if len(level0_groups) > 0:
                f.write(f"Level 0 groups = {len(level0_groups)}\n")
                f.write(f"Level 1 groups = {len(level1_groups)}\n")
                f.write(f"Level 2 groups = {len(level2_groups)}\n")
                f.write(f'All hosts = {",".join(all_hosts)}\n')

    def _prepare_analysis(self, workspace):
        self._process_id_list()
        self._process_physical_hosts()

    figure_of_merit(
        "machine-type",
        fom_regex=r".*machineTypes/(?P<machine>.*)",
        group_name="machine",
        log_file="{experiment_run_dir}/gcp-metadata.machine-type.log",
    )
    figure_of_merit(
        "image",
        fom_regex=r"(?P<image>.*global/images.*)",
        group_name="image",
        log_file="{experiment_run_dir}/gcp-metadata.image.log",
    )

    # This is intentionally left singular, to get the hostname of the "parent" or "root" process
    figure_of_merit(
        "ghostname",
        fom_regex=r"(?P<ghostname>.*internal)",
        group_name="ghostname",
        log_file="{experiment_run_dir}/gcp-metadata.hostname.log",
    )

    # This returns a list of all known gids in the job
    figure_of_merit(
        "gids",
        fom_regex=r"(?P<gid>.*)",
        group_name="gid",
        log_file="{experiment_run_dir}/gcp-metadata.id_list.log",
    )

    figure_of_merit(
        "project-id",
        fom_regex=r"(?P<numeric_project_id>\d+)",
        group_name="numeric_project_id",
        log_file="{experiment_run_dir}/gcp-metadata.numeric-project-id.log",
    )

    figure_of_merit(
        "Level {level_num} Groups",
        fom_regex="Level (?P<level_num>[0-9]) groups = (?P<num_groups>[0-9]+)",
        log_file="{experiment_run_dir}/gcp-metadata.topology_summary.log",
        group_name="num_groups",
        units="",
    )

    figure_of_merit(
        "Level 0 Groups",
        fom_regex="Level 0 groups = (?P<num_groups>.*)",
        log_file="{experiment_run_dir}/gcp-metadata.topology_summary.log",
        group_name="num_groups",
        units="",
    )

    figure_of_merit(
        "All Hosts",
        fom_regex="All hosts = (?P<hostlist>.*)",
        log_file="{experiment_run_dir}/gcp-metadata.topology_summary.log",
        group_name="hostlist",
        units="",
    )
