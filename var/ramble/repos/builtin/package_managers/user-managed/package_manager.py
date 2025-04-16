# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.pkgmankit import *  # noqa: F403


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

    # TODO: do we already have this somewhere more generic?
    def _spec_to_dict(self, spec):
        parts = spec.split("@")

        spec_dict = {}
        spec_dict["name"] = parts[0]
        spec_dict["version"] = parts[1]

        return spec_dict

    def get_package_list(self, workspace):
        """Augment the owning experiment's results with software stack information

        This is called by the `add_software_to_results` phase registered in the base
        package manager class.
        """
        sw = workspace.get_software_dict()
        pkg_list = []

        if sw:
            for key, package in sw["packages"].items():
                pkg_list.append(self._spec_to_dict(package["pkg_spec"]))

        return pkg_list
