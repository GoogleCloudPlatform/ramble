# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.pkgmankit import *  # noqa: F403


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
