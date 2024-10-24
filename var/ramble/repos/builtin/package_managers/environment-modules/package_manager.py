# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.pkgmankit import *  # noqa: F403

import os
import llnl.util.filesystem as fs

import ramble.util.hashing

import ramble.config
from ramble.util.shell_utils import source_str


class EnvironmentModules(PackageManagerBase):
    """Definition for using environment-modules as a package manager

    This definition allows experiments to use environment-modules to manage the
    software used in an experiment. It assumes the `module` command will be in
    the path of the experiment at execution time.
    """

    name = "environment-modules"

    maintainers("douglasjacobsen")

    _spec_prefix = "environment_modules"

    register_phase(
        "write_module_commands",
        pipeline="setup",
        run_before=["make_experiments"],
    )

    def _generate_loads_content(self, workspace):
        if not hasattr(self, "_load_string"):
            app_context = self.app_inst.expander.expand_var_name(
                self.keywords.env_name
            )

            require_env = self.environment_required()

            software_envs = workspace.software_environments
            software_env = software_envs.render_environment(
                app_context, self.app_inst.expander, self, require=require_env
            )

            load_content = []

            if software_env is not None:
                for spec in software_envs.package_specs_for_environment(
                    software_env
                ):
                    load_content.append(f"module load {spec}")

            self._load_string = "\n".join(load_content)

        return self._load_string

    def populate_inventory(
        self, workspace, force_compute=False, require_exist=False
    ):
        self.app_inst.hash_inventory["package_manager"].append(
            {
                "name": self.name,
            }
        )

        env_path = self.app_inst.expander.env_path
        env_hash = ramble.util.hashing.hash_string(
            self._generate_loads_content(workspace)
        )

        self.app_inst.hash_inventory["software"].append(
            {
                "name": env_path.replace(workspace.root + os.path.sep, ""),
                "digest": env_hash,
            }
        )

    def _write_module_commands(self, workspace, app_inst=None):
        env_path = self.app_inst.expander.env_path

        module_file_path = os.path.join(env_path, "module_loads")

        fs.mkdirp(env_path)

        loads_content = self._generate_loads_content(workspace)

        with open(module_file_path, "w+") as f:
            f.write(loads_content)

    register_builtin("module_load", required=True)

    def module_load(self):
        shell = ramble.config.get("config:shell")
        return [f"{source_str(shell)} " + "{env_path}/module_loads"]

    def _add_software_to_results(self, workspace, app_inst=None):
        app_context = self.app_inst.expander.expand_var_name(
            self.keywords.env_name
        )

        require_env = self.environment_required()

        software_envs = workspace.software_environments
        software_env = software_envs.render_environment(
            app_context, self.app_inst.expander, self, require=require_env
        )

        if self._spec_prefix not in app_inst.result.software:
            app_inst.result.software[self._spec_prefix] = []

        package_list = app_inst.result.software[self._spec_prefix]

        if software_env is not None:
            for spec in software_envs.package_specs_for_environment(
                software_env
            ):
                parts = spec.split("/")
                name = parts[0]
                version = "/".join(parts[1:]) if len(parts) > 1 else ""
                package_list.append(
                    {"name": name, "version": version, "variants": ""}
                )
