# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.pkgmankit import *  # noqa: F403


class UserManagedSoftwareInfo(ramble.package_manager.SoftwareInfo):
    def parse_from_spec(self, spec):
        parts = spec.split("@")

        if len(parts) >= 1:
            self.name = parts[0]
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

    register_phase(
        "define_requirements",
        pipeline="setup",
        run_before=["get_inputs"],
    )

    def _define_requirements(self, workspace, app_inst=None):
        """Define requirements for user managed software stack

        Extracts all required packages from experiments and modifiers, then
        creates required variables to convey the installation locations to
        Ramble.
        """

        if app_inst is None:
            package_objects = [(None, self)]
        else:
            package_objects = app_inst._objects()

        for _, obj in package_objects:
            for pkgname in obj.required_packages.keys():
                app_inst.keywords.update_keys(
                    {
                        f"{pkgname}_path": {
                            "type": ramble.keywords.key_type.required,
                            "level": ramble.keywords.output_level.variable,
                        }
                    }
                )

        app_inst.validate_experiment()

    def get_package_list(self, workspace):
        """Augment the owning experiment's results with software stack information

        This is called by the `add_software_to_results` phase registered in the base
        package manager class.
        """
        sw = workspace.get_software_dict()
        pkg_list = []

        app_inst = self.app_inst

        env_context = self.app_inst.expander.expand_var_name(
            self.keywords.env_name
        )
        require_env = False
        software_envs = workspace.software_environments
        software_env = software_envs.render_environment(
            env_context, self.app_inst.expander, self, require=require_env
        )

        if software_env:
            for pkg_spec in software_envs.package_specs_for_environment(
                software_env
            ):
                software_info = UserManagedSoftwareInfo()
                software_info.parse_from_spec(pkg_spec)
                pkg_list.append(software_info)

        return pkg_list
