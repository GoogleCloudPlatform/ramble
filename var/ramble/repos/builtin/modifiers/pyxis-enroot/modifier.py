# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.modkit import *
from ramble.util.hashing import hash_file, hash_string
from spack.util.path import canonicalize_path

import llnl.util.filesystem as fs


class PyxisEnroot(BasicModifier):
    """Modifier to aid configuring pyxis-enroot based execution environments

    Pyxis is a container plugin for slurm developed by NVIDIA.
    https://github.com/NVIDIA/pyxis

    Enroot is a tool to convert containers into unprivileged sandboxes that can
    be executed in slurm with Pyxis.
    https://github.com/NVIDIA/enroot


    This modifier requires the following input variables:
    - container_uri: This needs to be a container URI that is formatted for and
                    `enroot import` command. For examples, see
                    https://github.com/NVIDIA/enroot/blob/master/doc/cmd/import.md
    - container_name: This is the name of the resulting squashfs file that enroot produces

    The following modifier variables are optional inputs:
    - container_dir
    - container_extract_paths

    The following modifier variables are generated outputs:
    - container_mounts
    - container_env_vars
    """

    container_extension = "sqsh"

    container_hash_file_extension = "sha256"

    name = "pyxis-enroot"

    tags("container", "slurm")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode for pyxis-enroot")
    mode(
        "no_provenance",
        description="Standard execution mode without provenance tracking",
    )
    default_mode("standard")

    required_variable("container_name")
    required_variable("container_uri")

    modifier_variable(
        "container_mounts",
        default="",
        description="Comma delimited list of mount points for the container. Filled in by modifier",
        modes=["standard", "no_provenance"],
    )

    modifier_variable(
        "container_env_vars",
        default="",
        description="Comma delimited list of environments to import into container. Filled in by modifier",
        modes=["standard", "no_provenance"],
    )

    modifier_variable(
        "container_dir",
        default="{workload_input_dir}",
        description="Directory where the container sqsh will be stored",
        modes=["standard", "no_provenance"],
    )

    modifier_variable(
        "container_extract_dir",
        default="{workload_input_dir}",
        description="Directory where the extracted paths will be stored",
        modes=["standard", "no_provenance"],
    )

    modifier_variable(
        "container_path",
        default="{container_dir}/{container_name}." + container_extension,
        description="Full path to the container sqsh file",
        modes=["standard", "no_provenance"],
    )

    modifier_variable(
        "container_extract_paths",
        default="[]",
        description="List of paths to extract from the sqsh file into the {workload_input_dir}. "
        + "Will have paths of {workload_input_dir}/enroot_extractions/{path_basename}",
        modes=["standard", "no_provenance"],
        track_used=False,
    )

    def __init__(self, file_path):
        super().__init__(file_path)

        self.enroot_runner = None
        self.unsquashfs_runner = None

    def _build_commands(self, dry_run=False):
        """Construct command runners for enroot and unsquashfs"""
        if self.enroot_runner is None:
            self.enroot_runner = CommandRunner(
                name="enroot", command="enroot", dry_run=dry_run
            )

        if self.unsquashfs_runner is None:
            self.unsquashfs_runner = CommandRunner(
                name="unsquashfs", command="unsquashfs", dry_run=dry_run
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
                add_mod = (
                    add_mod
                    or self._usage_mode in self.variable_modifications
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
        "import_sqsh",
        pipeline="setup",
        run_after=["get_inputs"],
        run_before=["make_experiments"],
    )

    def _import_sqsh(self, workspace, app_inst=None):
        """Import the container uri as a sqsh file

        Extract the container uri and path from the experiment, and import
        (using enroot) into the target container_dir.
        """

        self._build_commands(workspace.dry_run)

        uri = self.expander.expand_var_name("container_uri")

        container_dir = canonicalize_path(
            self.expander.expand_var_name("container_dir")
        )
        container_path = canonicalize_path(
            self.expander.expand_var_name("container_path")
        )

        import_args = ["import", "-o", container_path, "--", uri]

        if not os.path.exists(container_path):
            if not workspace.dry_run:
                fs.mkdirp(container_dir)
            self.enroot_runner.execute(self.enroot_runner.command, import_args)
        else:
            logger.msg(f"Container is already imported at {container_path}")

    register_phase(
        "extract_from_sqsh",
        pipeline="setup",
        run_after=["import_sqsh"],
        run_before=["make_experiments"],
    )

    def _extract_from_sqsh(self, workspace, app_inst=None):
        """Extract paths from the sqsh file into the workload inputs path"""

        self._build_commands(workspace.dry_run)

        extract_paths = self.expander.expand_var_name(
            "container_extract_paths", typed=True, merge_used_stage=False
        )
        self.expander.flush_used_variable_stage()

        if isinstance(extract_paths, str):
            extract_paths = [extract_paths]

        if isinstance(extract_paths, list) and len(extract_paths) > 0:
            container_extract_dir = self.expander.expand_var_name(
                "container_extract_dir"
            )
            container_path = self.expander.expand_var_name("container_path")

            unsquash_args = [
                "-f",
                "-dest",
                container_extract_dir,
                container_path,
            ]

            for extract_path in extract_paths:
                expanded_path = canonicalize_path(
                    self.expander.expand_var(extract_path)
                )
                self.unsquashfs_runner.execute(
                    self.unsquashfs_runner.command,
                    unsquash_args + [expanded_path],
                )

    def artifact_inventory(self, workspace, app_inst=None):
        """Return hash of container uri and sqsh file if they exist

        Args:
            workspace (Workspace): Reference to workspace
            app_inst (ApplicationBase): Reference to application instance

        Returns:
            (dict): Artifact inventory for container attributes
        """
        container_name = self.expander.expand_var_name("container_name")
        container_path = canonicalize_path(
            self.expander.expand_var_name("container_path")
        )
        container_uri = self.expander.expand_var_name("container_uri")
        inventory = []

        if self._usage_mode == "no_provenance":
            return inventory

        inventory.append(
            {
                "container_uri": container_uri,
                "digest": hash_string(container_uri),
            }
        )

        if os.path.isfile(container_path):

            hash_file_path = (
                container_path + "." + self.container_hash_file_extension
            )

            if os.path.exists(hash_file_path):
                with open(hash_file_path, "r") as f:
                    container_hash = f.read()

            else:
                container_hash = hash_file(container_path)

                with open(hash_file_path, "w+") as f:
                    f.write(container_hash)

            inventory.append(
                {"container_name": container_name, "digest": container_hash}
            )

        return inventory

    # TODO: Decide on backing up sqsh files.
    #       The following code works. But there's not a nice way to auto-extract the sqsh file out of the mirror
    #       This is because the import functionality uses `enroot` directly, which bypasses
    #       the mirror logic.
    #  register_phase("mirror_containers", pipeline="mirror", run_after=["mirror_inputs"])

    #  def _mirror_containers(self, workspace, app_inst=None):
    #     from ramble.util.hashing import hash_file
    #     import ramble.util.lock as lk
    #     import llnl.util.filesystem as fs
    #     mirror_lock = lk.Lock(os.path.join(workspace.input_mirror_path, ".ramble-mirror"))

    #     container_name = self.expander.expand_var_name('container_name')
    #     container_path = self.expander.expand_var_name('container_path')
    #     container_hash = hash_file(container_path)
    #     container_fetcher = ramble.fetch_strategy.URLFetchStrategy(
    #     url=container_path,
    #     expand=False,
    #     input_name=container_name,
    #     target_dir=container_path,
    #     extension=self.container_extension,
    #     sha256=container_hash,
    #     )

    #     file_name = container_name + "." + self.container_extension
    #     fetch_dir = os.path.join(workspace.input_mirror_path, "enroot")

    #     fs.mkdirp(fetch_dir)

    #     with lk.WriteTransaction(mirror_lock):
    #     mirror_paths = ramble.mirror.mirror_archive_paths(
    #     container_fetcher, container_path
    #     )

    #     stage = ramble.stage.InputStage(
    #     container_fetcher,
    #     name=container_name,
    #     path=fetch_dir,
    #     mirror_paths=mirror_paths,
    #     lock=False,
    #     )

    #     stage.cache_mirror(
    #     workspace.input_mirror_cache,
    #     workspace.input_mirror_stats
    #     )
