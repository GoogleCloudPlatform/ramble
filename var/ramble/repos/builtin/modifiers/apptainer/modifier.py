# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import re
import os

from ramble.modkit import *
from ramble.util.hashing import hash_string
from spack.util.path import canonicalize_path

import llnl.util.filesystem as fs


class Apptainer(BasicModifier):
    """Apptainer is a container platform. It allows you to create and run
    containers that package up pieces of software in a way that is portable and
    reproducible. You can build a container using Apptainer on your laptop, and
    then run it on many of the largest HPC clusters in the world, local
    university or company clusters, a single server, in the cloud, or on a
    workstation down the hall. Your container is a single file, and you don’t
    have to worry about how to install all the software you need on each
    different operating system."""

    container_extension = "sif"
    name = "apptainer"

    tags("container")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode for apptainer")
    default_mode("standard")

    required_variable(
        "container_name",
        description="The variable controls the name of the resulting container file. "
        "It will be of the format {container_name}.{container_extension}.",
    )

    required_variable(
        "container_uri",
        description="The variable controls the URI the container is pulled from. "
        "This should be of the format that would be input into `apptainer pull <uri>`.",
    )

    modifier_variable(
        "container_mounts",
        default="",
        description="Comma delimited list of mount points for the container. Filled in by modifier",
        modes=["standard"],
    )

    modifier_variable(
        "container_env_vars",
        default="",
        description="Comma delimited list of environments to import into container. Filled in by modifier",
        modes=["standard"],
    )

    modifier_variable(
        "container_dir",
        default="{workload_input_dir}",
        description="Directory where the container sqsh will be stored",
        modes=["standard"],
    )

    modifier_variable(
        "container_extract_dir",
        default="{workload_input_dir}",
        description="Directory where the extracted paths will be stored",
        modes=["standard"],
    )

    modifier_variable(
        "container_path",
        default="{container_dir}/{container_name}." + container_extension,
        description="Full path to the container sqsh file",
        modes=["standard"],
    )

    modifier_variable(
        "container_extract_paths",
        default="[]",
        description="List of paths to extract from the sqsh file into the {workload_input_dir}. "
        + "Will have paths of {workload_input_dir}/enroot_extractions/{path_basename}",
        modes=["standard"],
        track_used=False,
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

    def __init__(self, file_path):
        super().__init__(file_path)

        self.apptainer_runner = None

    def _build_commands(self, app_inst=None, dry_run=False):
        """Construct command runner for apptainer"""

        if self.apptainer_runner is None:
            path = None
            # If using spack, load spack environment before getting apptainer exec path
            if app_inst.package_manager is not None:
                if app_inst.package_manager.spec_prefix() == "spack":
                    app_inst.package_manager.runner.activate()
                    _, base = app_inst.package_manager.runner.get_package_path(
                        "apptainer"
                    )
                    app_inst.package_manager.runner.deactivate()

                    if base and os.path.exists(base):
                        test_path = os.path.join(base, "bin")
                        if os.path.isdir(test_path):
                            path = test_path

            self.apptainer_runner = CommandRunner(
                name="apptainer",
                command="apptainer",
                dry_run=dry_run,
                path=path,
            )

    register_phase(
        "define_container_variables",
        pipeline="setup",
        run_before=["get_inputs"],
    )

    def _define_container_variables(self, workspace, app_inst=None):
        """Define helper variables for working with enroot experiments

        To ensure it is defined properly, construct a comma delimited list of
        environment variable names that will be added into the
        container_env_vars variable.
        """

        def extract_names(itr, name_set=set()):
            """Extract names of environment variables from the environment variable action sets

            Given an iterator over environment variable action sets, extract
            the names of the environment variables.

            Modifies the name_set argument inplace.
            """
            for action, conf in itr:
                if action in ["set", "unset"]:
                    for name in conf:
                        name_set.add(name)
                elif action == "prepend":
                    for group in conf:
                        for name in group["paths"]:
                            name_set.add(name)
                elif action == "append":
                    for group in conf:
                        for name in group["vars"]:
                            name_set.add(name)

        # Only define variables if mode is standard
        if self._usage_mode == "standard":
            # Define container_env-vars
            set_names = set()

            for env_var_set in app_inst._env_variable_sets:
                extract_names(env_var_set.items(), set_names)

            for mod_inst in app_inst._modifier_instances:
                extract_names(mod_inst.all_env_var_modifications(), set_names)

            env_var_list = ",".join(set_names)
            app_inst.define_variable("container_env_vars", env_var_list)

            # Define container_mounts
            input_mounts = app_inst.expander.expand_var("{container_mounts}")

            prefix = ""
            if len(input_mounts) > 0:
                prefix = ","

            exp_mount = "{experiment_run_dir}:{experiment_run_dir}"
            expanded_exp_mount = app_inst.expander.expand_var(exp_mount)

            if (
                exp_mount not in input_mounts
                and expanded_exp_mount not in input_mounts
            ):
                add_mod = self._usage_mode not in self.variable_modifications
                add_mod = add_mod or (
                    self._usage_mode in self.variable_modifications
                    and "container_mounts"
                    not in self.variable_modifications[self._usage_mode]
                )
                if add_mod:
                    self.variable_modification(
                        "container_mounts",
                        modification=prefix + exp_mount,
                        method="append",
                        mode=self._usage_mode,
                    )

    register_phase(
        "pull_sif",
        pipeline="setup",
        run_after=["get_inputs"],
        run_before=["make_experiments"],
    )

    def _pull_sif(self, workspace, app_inst=None):
        """Import the container uri as an apptainer sif file

        Extract the container uri and path from the experiment, and import
        (using apptainer) into the target container_dir.
        """

        self._build_commands(app_inst, workspace.dry_run)

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

        self._build_commands(app_inst, workspace.dry_run)

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
