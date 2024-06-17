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


class EnvironmentModules(PackageManagerBase):
    """Definition for using environment-modules as a package manager

    This definition allows experiments to use environment-modules to manage the
    software used in an experiment. It assumes the `module` command will be in
    the path of the experiment at execution time.
    """

    name = "environment-modules"

    maintainers("douglasjacobsen")

    def get_spec_str(self, pkg, all_pkgs, compiler):
        return pkg.spec

    register_phase(
        "write_module_commands",
        pipeline="setup",
        run_before=["make_experiments"],
    )

    def populate_inventory(
        self, workspace, force_compute=False, require_exist=False
    ):
        env_path = self.app_inst.expander.env_path

        self.app_inst.hash_inventory["package_manager"].append(
            {
                "name": self.name,
            }
        )

        env_hash = ramble.util.hashing.hash_file(
            os.path.join(env_path, "module_loads")
        )

        self.app_inst.hash_inventory["software"].append(
            {
                "name": env_path.replace(workspace.root + os.path.sep, ""),
                "digest": env_hash,
            }
        )

    def _write_module_commands(self, workspace, app_inst=None):

        app_context = self.app_inst.expander.expand_var_name(
            self.keywords.env_name
        )

        require_env = self.environment_required()

        software_envs = workspace.software_environments
        software_env = software_envs.render_environment(
            app_context, self.app_inst.expander, self, require=require_env
        )

        env_path = self.app_inst.expander.env_path

        module_file_path = os.path.join(env_path, "module_loads")

        fs.mkdirp(env_path)

        module_file = open(module_file_path, "w+")

        if software_env is not None:
            for spec in software_envs.package_specs_for_environment(
                software_env
            ):
                module_file.write(f"module load {spec}\n")
        module_file.close()

    register_builtin("module_load", required=True)

    def module_load(self):
        return [" . {env_path}/module_loads"]
