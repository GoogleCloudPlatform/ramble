# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from typing import List

from ramble.pkgmankit import *


class UserManagedSoftwareInfo(ramble.software_info.SoftwareInfo):
    def parse_from_spec(self, spec):
        parts = spec.split("@")

        if len(parts) >= 1:
            self.name = parts[0].strip()
        if len(parts) >= 2:
            self.version = parts[1]


class UserManaged(PackageManagerBase):
    """Package manager representing a user managed environment.

    This package manager is used when the software required for the experiments
    is manually installed outside of Ramble. Generally, a user will need to
    convey the paths to these installed packages to Ramble through specific
    variable definitions.
    """

    name = "user-managed"

    _spec_prefix = "user_managed"

    requires_software_environment = False

    def __init__(self, file_path):
        super().__init__(file_path)

    def package_name_from_spec(self, spec):
        return spec

    def set_required_variables(self, app_inst=None):
        """Define requirements for user managed software stack

        Extracts all required packages from experiments and modifiers, then
        creates required variables to convey the installation locations to
        Ramble.
        """
        for _, obj in app_inst.objects():
            for pkgname in obj.required_packages.keys():
                app_inst.keywords.update_keys(
                    {
                        f"{pkgname}_path": {
                            "type": ramble.keywords.key_type.required,
                            "level": ramble.keywords.output_level.variable,
                        }
                    }
                )

    def get_package_list(self, workspace):
        """Augment the owning experiment's results with software stack information

        This is called by the `add_software_to_results` phase registered in the base
        package manager class.
        """
        pkg_list = []

        app_inst = self.app_inst

        env_context = app_inst.expander.expand_var_name(self.keywords.env_name)
        require_env = False
        software_envs = workspace.software_environments
        software_env = software_envs.render_environment(
            env_context, app_inst.expander, self, require=require_env
        )

        if software_env:
            for pkg_spec in software_envs.package_specs_for_environment(
                software_env
            ):
                software_info = UserManagedSoftwareInfo()
                software_info.parse_from_spec(pkg_spec)
                pkg_list.append(software_info)

        return pkg_list

    def environment_load_commands(self) -> List[str]:
        return []

    def environment_unload_commands(self) -> List[str]:
        return []
