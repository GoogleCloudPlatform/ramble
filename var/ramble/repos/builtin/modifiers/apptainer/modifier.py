# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import re

import llnl.util.filesystem as fs

from ramble.base_mod.builtin.container_base import ContainerBase
from ramble.modkit import *
from ramble.util.hashing import hash_string

from spack.util.path import canonicalize_path


class Apptainer(ContainerBase):
    """Apptainer is a container platform. It allows you to create and run
    containers that package up pieces of software in a way that is portable and
    reproducible. You can build a container using Apptainer on your laptop, and
    then run it on many of the largest HPC clusters in the world, local
    university or company clusters, a single server, in the cloud, or on a
    workstation down the hall. Your container is a single file, and you don’t
    have to worry about how to install all the software you need on each
    different operating system."""

    container_extension = "sif"
    _runtime = "apptainer"
    name = "apptainer"

    tags("container")

    maintainers("douglasjacobsen")

    required_variable(
        "container_name",
        description="The variable controls the name of the resulting container file. "
        "It will be of the format {container_name}.{container_extension}.",
    )

    modifier_variable(
        "container_dir",
        default="{workload_input_dir}",
        description="Directory where the container sqsh will be stored",
        modes=["standard"],
    )

    modifier_variable(
        "container_path",
        default="{container_dir}/{container_name}." + container_extension,
        description="Full path to the container sqsh file",
        modes=["standard"],
    )

    modifier_variable(
        "apptainer_run_args",
        default="--bind {container_mounts}",
        description="Arguments to pass into `apptainer run` while executing the experiments",
        modes=["standard"],
    )

    variable_modification(
        "mpi_command",
        "apptainer run {apptainer_run_args} {container_path}",
        method="append",
        modes=["standard"],
    )

    register_phase(
        "pull_container",
        pipeline="setup",
        run_after=["make_experiments"],
    )

    def _pull_container(self, workspace, app_inst=None):
        """Import the container uri as an apptainer sif file

        Extract the container uri and path from the experiment, and import
        (using apptainer) into the target container_dir.
        """

        self._build_runner(
            runtime=self._runtime, app_inst=app_inst, dry_run=workspace.dry_run
        )

        uri = self.expander.expand_var_name("container_uri")

        container_dir = canonicalize_path(
            self.expander.expand_var_name("container_dir")
        )
        container_path = canonicalize_path(
            self.expander.expand_var_name("container_path")
        )

        pull_args = ["pull", container_path, uri]

        if not os.path.exists(container_path):
            if not workspace.dry_run:
                fs.mkdirp(container_dir)
            self.apptainer_runner.execute(
                self.apptainer_runner.command, pull_args
            )
        else:
            logger.msg(f"Container is already pulled at {container_path}")

    def artifact_inventory(self, workspace, app_inst=None):
        """Return hash of container uri and sqsh file if they exist

        Args:
            workspace (Workspace): Reference to workspace
            app_inst (ApplicationBase): Reference to application instance

        Returns:
            (dict): Artifact inventory for container attributes
        """

        self._build_runner(
            runtime=self._runtime, app_inst=app_inst, dry_run=workspace.dry_run
        )

        id_regex = re.compile(r"\s*ID:\s*(?P<id>\S+)")
        container_name = self.expander.expand_var_name("container_name")
        container_uri = self.expander.expand_var_name("container_uri")
        container_path = canonicalize_path(
            self.expander.expand_var_name("container_path")
        )
        header_args = ["sif", "header", container_path]

        inventory = []

        inventory.append(
            {
                "container_uri": container_uri,
                "digest": hash_string(container_uri),
            }
        )

        container_id = None

        if os.path.isfile(container_path):
            header = self.apptainer_runner.execute(
                self.apptainer_runner.command, header_args, return_output=True
            )

            search_match = id_regex.search(header)

            if search_match:
                container_id = search_match.group("id")

        if container_id:
            inventory.append(
                {"container_name": container_name, "digest": container_id}
            )
        else:
            inventory.append(
                {"container_name": container_name, "digest": None}
            )

        return inventory
