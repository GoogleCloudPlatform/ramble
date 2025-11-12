# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.pkgmankit import *


class WhenPackageManager(PackageManagerBase):
    name = "when-package-manager"

    variant(
        "package_manager_included",
        default=False,
        values=[True, False],
        description="Test variant",
    )

    with when("+package_manager_included"):
        package_manager_variable(
            "pm_var_test", default="included", description="Test variable"
        )

    variant(
        "package_manager_env_var_included",
        default=False,
        values=[True, False],
        description="Test package manager env vars",
    )

    with when("+package_manager_env_var_included"):
        environment_variable(
            "PACKAGE_ENV_VAR",
            value="PKG_ENV_VAR_SET",
            description="Test env variable",
        )

    variant(
        "pkg_man_required_variable",
        default=False,
        values=[True, False],
        description="Test required variable",
    )

    required_variable(
        "test_pkg_man_required_variable",
        description="Test required variable",
        when=["+pkg_man_required_variable"],
    )

    variant(
        "pkg_man_required_key",
        default=False,
        values=[True, False],
        description="Test required key",
    )

    required_variable(
        "test_pkg_man_required_key",
        results_level="key",
        description="Test required key",
        when=["+pkg_man_required_key"],
    )

    def get_package_list(self, workspace):
        del workspace
        return []

    def package_name_from_spec(self, spec: str) -> str:
        return spec

    def environment_load_commands(self) -> List[str]:
        return []

    def environment_unload_commands(self) -> List[str]:
        return []
