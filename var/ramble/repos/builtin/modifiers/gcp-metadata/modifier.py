# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

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
    mode(
        "local", description="Local execution (disables parallel prefix/pdssh)"
    )
    default_mode("standard")

    software_spec("pdsh", pkg_spec="pdsh", package_manager="spack*")

    required_variable("hostlist", modes=["standard"])

    modifier_variable(
        "metadata_parallel_prefix",
        default="pdsh -R ssh -N -w {hostlist} '",
        modes=["standard"],
        description="Express how parlalelism should be done between nodes",
    )
    modifier_variable(
        "metadata_parallel_prefix",
        default="",
        modes=["local"],
        description="Express how parlalelism should be done between nodes",
    )

    # Need to close any open `'` we leave in the prefix
    modifier_variable(
        "metadata_parallel_suffix",
        default="'",
        modes=["standard"],
        description="Optional suffix for {metadata_parallel_prefix}",
    )
    modifier_variable(
        "metadata_parallel_suffix",
        default="",
        modes=["local"],
        description="Optional suffix for {metadata_parallel_prefix}",
    )

    executable_modifier("gcp_metadata_exec")

    def gcp_metadata_exec(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        if hasattr(self, "_already_applied"):
            return [], []

        self._already_applied = True

        post_cmds = []
        pre_cmds = []

        if self._usage_mode != "local":
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
            # type, end point, per_node, log_name
            ("instance", "machine-type", False, None),
            ("instance", "image", False, None),
            ("instance", "hostname", False, None),
            (
                "instance",
                "id",
                True,
                None,
            ),  # True since we want the gid of every node
            ("project", "numeric-project-id", False, None),
            ("instance", "attributes/physical_host", True, None),
        ]

        n_nodes = int(self.expander.expand_var_name("n_nodes"))
        if n_nodes > 1 and self._usage_mode != "local":
            # Single-out the vm_id of the executing-node
            payloads.append(("instance", "id", False, "main-gid"))

        for type, end_point, per_node, log_name in payloads:
            prefix = ""
            suffix = ""
            if per_node:
                prefix = self.expander.expand_var("{metadata_parallel_prefix}")
                suffix = self.expander.expand_var("{metadata_parallel_suffix}")
            log_name = (
                log_name if log_name is not None else end_point.split("/")[-1]
            )
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

        if self._usage_mode != "local":
            pre_cmds.append(
                CommandExecutable(
                    "restore-old-loglevel",
                    template=['export PDSH_SSH_ARGS_APPEND="$old_pdsh_args"'],
                )
            )

        return pre_cmds, post_cmds

    def get_vm_id_list(self):
        ids = set()
        exp_run_dir = self.expander.expand_var_name("experiment_run_dir")
        file_name = os.path.join(exp_run_dir, "gcp-metadata.id.log")
        if os.path.isfile(file_name):
            with open(file_name) as f:
                for cur_id in f.readlines():
                    cur_id = cur_id.strip()
                    if cur_id.isnumeric():
                        ids.add(cur_id)
        return sorted(ids)

    def _process_id_list(self):
        ids = self.get_vm_id_list()

        if ids:
            with open(
                self.expander.expand_var(
                    "{experiment_run_dir}/gcp-metadata.id_list.log"
                ),
                "w+",
            ) as f:
                f.write(", ".join(sorted(ids)))

    def _process_physical_hosts(self, workspace):
        run_dir = self.expander.expand_var("{experiment_run_dir}")
        log_path = get_file_path(
            os.path.join(
                run_dir,
                "gcp-metadata.physical_host.log",
            ),
            workspace,
        )
        if not os.path.isfile(log_path):
            return

        level0_groups = set()
        level1_groups = set()
        level2_groups = set()
        all_hosts = set()

        with open(log_path) as f:
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
            os.path.join(run_dir, "gcp-metadata.topology_summary.log"),
            "w+",
        ) as f:
            if len(level0_groups) > 0:
                # The group level name comes from https://cloud.google.com/compute/docs/instances/use-compact-placement-policies#verify-vm-location.
                f.write(f"Level 0 groups (cluster) = {len(level0_groups)}\n")
                f.write(f"Level 1 groups (rack) = {len(level1_groups)}\n")
                f.write(f"Level 2 groups (host) = {len(level2_groups)}\n")
                f.write(f'All hosts = {",".join(all_hosts)}\n')

    def _prepare_analysis(self, workspace):
        self._process_id_list()
        self._process_physical_hosts(workspace)

    figure_of_merit(
        "machine-type",
        fom_regex=r".*machineTypes/(?P<machine>.*)",
        group_name="machine",
        log_file="{experiment_run_dir}/gcp-metadata.machine-type.log",
        fom_type=FomType.INFO,
    )
    figure_of_merit(
        "image",
        fom_regex=r"(?P<image>.*global/images.*)",
        group_name="image",
        log_file="{experiment_run_dir}/gcp-metadata.image.log",
        fom_type=FomType.INFO,
    )

    # This is intentionally left singular, to get the hostname of the "parent" or "root" process
    figure_of_merit(
        "ghostname",
        fom_regex=r"(?P<ghostname>.*internal)",
        group_name="ghostname",
        log_file="{experiment_run_dir}/gcp-metadata.hostname.log",
        fom_type=FomType.INFO,
    )
    figure_of_merit(
        "main-gid",
        fom_regex=r"(?P<gid>.*)",
        group_name="gid",
        log_file="{experiment_run_dir}/gcp-metadata.main-gid.log",
        fom_type=FomType.INFO,
    )

    # This returns a list of all known gids in the job
    figure_of_merit(
        "gids",
        fom_regex=r"(?P<gid>.*)",
        group_name="gid",
        log_file="{experiment_run_dir}/gcp-metadata.id_list.log",
        fom_type=FomType.INFO,
    )

    figure_of_merit(
        "project-id",
        fom_regex=r"(?P<numeric_project_id>\d+)",
        group_name="numeric_project_id",
        log_file="{experiment_run_dir}/gcp-metadata.numeric-project-id.log",
        fom_type=FomType.INFO,
    )

    figure_of_merit(
        "Level {level_num} Groups ({level_name})",
        fom_regex=r"Level (?P<level_num>[0-9]) groups \((?P<level_name>[\w]+)\) = (?P<num_groups>[0-9]+)",
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
