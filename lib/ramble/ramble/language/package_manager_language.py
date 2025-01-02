# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from typing import Optional

import ramble.language.language_helpers
import ramble.language.language_base
import ramble.language.shared_language


class PackageManagerMeta(ramble.language.shared_language.SharedMeta):
    _directive_names = set()
    _directives_to_be_executed = []


package_manager_directive = PackageManagerMeta.directive


@package_manager_directive("package_manager_variables")
def package_manager_variable(
    name: str,
    default,
    description: str,
    values: Optional[list] = None,
    expandable: bool = True,
    **kwargs,
):
    """Define a variable for this package manager

    Args:
        name (str): Name of variable to define
        default: Default value of variable definition
        description (str): Description of variable's purpose
        values (list): Optional list of suggested values for this variable
        expandable (bool): True if the variable should be expanded, False if not.
    """

    def _define_package_manager_variable(pm):
        import ramble.workload

        pm.package_manager_variables[name] = ramble.workload.WorkloadVariable(
            name,
            default=default,
            description=description,
            values=values,
            expandable=expandable,
        )

    return _define_package_manager_variable
