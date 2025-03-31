# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import re

from ramble.base_mod.builtin.container_base import ContainerBase
from ramble.modkit import *
from ramble.util.hashing import hash_string


class Docker(ContainerBase):
    """Docker is a set of platform as a service (PaaS) products that use
    OS-level virtualization to deliver software in packages called
    containers. The service has both free and premium tiers. The software
    that hosts the containers is called Docker Engine. It was first released
    in 2013 and is developed by Docker, Inc.

    When mode == build_only or mode == standard_with_build, this modifier will
    perform a docker build on a Dockerfile. After creating the container image,
    this modifier will pre-define container_uri and container_name for
    subsequent containerizer modifiers to ingest.
    """

    name = "docker"

    _runtime = "docker"
    _pull_command = "docker pull"

    maintainers("douglasjacobsen")

    mode(
        "build_only",
        description="Only perform a docker build, but do not inject docker execute commands",
    )

    mode(
        "standard_with_build",
        description="Standard docker mode, with a container build before experiment execution",
    )

    modifier_variable(
        "docker_run_args",
        default="{container_mounts} -e {container_env_vars}",
        description="Arguments to pass into `docker run` while executing the experiments. Contains --mount flags",
        modes=["standard", "standard_with_build"],
    )

    required_variable(
        "dockerfile_path",
        description="Path to Dockerfile when trying to build a container",
        modes=["build_only", "standard_with_build"],
    )

    required_variable(
        "docker_tag_name",
        description="Name of tag to apply when building docker container",
        modes=["build_only", "standard_with_build"],
    )

    required_variable(
        "docker_tag_version",
        description="Version of tag to apply when building docker container",
        modes=["build_only", "standard_with_build"],
    )

    variable_modification(
        "mpi_command",
        "docker run {docker_run_args} {container_uri}",
        method="append",
        modes=["standard"],
    )

    variable_modification(
        "mpi_command",
        "docker run {docker_run_args} {docker_tag_name}:{docker_tag_version}",
        method="append",
        modes=["standard_with_build"],
    )

    register_phase(
        "build_container",
        pipeline="setup",
        run_after=["get_inputs"],
        run_before=["pull_container", "make_experiments"],
    )

    modifier_variable(
        "container_mounts",
        default="",
        description="Comma delimited list of mount points for the container. Filled in by modifier",
        modes=["standard_with_build"],
    )

    modifier_variable(
        "container_env_vars",
        default="",
        description="Comma delimited list of environments to import into container. Filled in by modifier",
        modes=["standard_with_build"],
    )

    modifier_variable(
        "container_uri",
        default="dockerd://{docker_tag_name}:{docker_tag_version}",
        description="URI For built docker containers",
        modes=["build_only", "standard_with_build"],
    )

    modifier_variable(
        "container_name",
        default="{docker_tag_name}_{docker_tag_version}",
        description="Name for container file that was built",
        modes=["build_only", "standard_with_build"],
    )

    def _build_container(self, workspace, app_inst):
        if "build" not in self._usage_mode:
            return

        self._build_runner(
            runtime=self._runtime, app_inst=app_inst, dry_run=workspace.dry_run
        )

        container_tag = self.expander.expand_var(
            "{docker_tag_name}:{docker_tag_version}"
        )
        dockerfile_path = self.expander.expand_var_name("dockerfile_path")

        path = os.path.dirname(dockerfile_path)
        file_name = os.path.basename(dockerfile_path)

        cur_dir = os.getcwd()

        # Change into the directory with the dockerfile
        if not workspace.dry_run:
            if not os.path.isdir(path):
                logger.die(
                    f"Path {path} does not exist to build a docker container with."
                )
            os.chdir(path)

        build_args = ["build", "-t", container_tag, "-f", file_name, "."]

        self.docker_runner.execute(self.docker_runner.command, build_args)
        os.chdir(cur_dir)

    register_phase(
        "pull_container",
        pipeline="setup",
        run_after=["get_inputs"],
        run_before=["make_experiments"],
    )

    def _pull_container(self, workspace, app_inst=None):
        """Pull the container uri using docker"""

        if "build" in self._usage_mode:
            return

        self._build_runner(
            runtime=self._runtime, app_inst=app_inst, dry_run=workspace.dry_run
        )

        uri = self.expander.expand_var_name("container_uri")

        pull_args = ["pull", uri]

        self.docker_runner.execute(self.docker_runner.command, pull_args)

    register_phase(
        "format_docker_mounts",
        pipeline="setup",
        run_after=["define_container_variables"],
        run_before=["make_experiments"],
    )

    def _format_docker_mounts(self, workspace, app_inst=None):
        """Reformat container_mounts definition to follow docker convention.

        Args:
            workspace (Workspace): Reference to workspace
            app_inst (ApplicationBase): Reference to application instance
        """

        # Only reformat the mounts if docker is used to execute.
        if "standard" not in self._usage_mode:
            return

        # Extract modified variables for all modifiers up until this one
        modded_vars = {}
        for mod_inst in app_inst._modifier_instances:
            modded_vars.update(
                mod_inst.modded_variables(app_inst, modded_vars)
            )

            if mod_inst == self:
                break

        # Expand all container mounts
        container_mounts = app_inst.expander.expand_var_name(
            "container_mounts", extra_vars=modded_vars
        )

        # Define new formatting for container mounts
        mount_parts = container_mounts.split(",")
        mount_definitions = []
        for part in mount_parts:
            mount_paths = part.split(":")

            new_def = f"--mount type=bind,source={mount_paths[0]}"
            if len(mount_paths) > 1:
                new_def += f",dst={mount_paths[1]}"
            else:
                new_def += f",dst={mount_paths[0]}"
            mount_definitions.append(new_def)

        # Override definition of container mounts
        self.variable_modification(
            "container_mounts",
            modification=" ".join(mount_definitions),
            separator=" ",
            method="set",
            mode=self._usage_mode,
        )

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

        id_regex = re.compile(r'Id.*sha256:(?P<id>\S+)"')
        if "build" in self._usage_mode:
            container_uri = self.expander.expand_var(
                "{docker_tag_name}:{docker_tag_version}"
            )
        else:
            container_uri = self.expander.expand_var_name("container_uri")

        inventory = []
        inspect_args = ["inspect", container_uri]

        info = self.docker_runner.execute(
            self.docker_runner.command, inspect_args, return_output=True
        )

        container_id = None
        search_match = None
        if info:
            search_match = id_regex.search(info)

        if search_match:
            container_id = search_match.group("id")
        else:
            container_id = hash_string(container_uri)

        inventory.append(
            {
                "container_uri": container_uri,
                "container_id": container_id,
            }
        )

        return inventory
