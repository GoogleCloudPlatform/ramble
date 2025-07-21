# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from typing import Optional

import ramble.definitions.families
import ramble.language.language_base
import ramble.language.language_helpers
import ramble.language.shared_language


class PackageManagerMeta(ramble.language.shared_language.SharedMeta):
    _directive_names = set()
    _directives_to_be_executed = []


package_manager_directive = PackageManagerMeta.directive


@package_manager_directive(dicts=())
def package_manager_variable(
    name: str,
    default,
    description: str,
    values: Optional[list] = None,
    expandable: bool = True,
    track_used: bool = False,
    when=None,
    **kwargs,
):
    """Define a variable for this package manager

    Args:
        name (str): Name of variable to define
        default: Default value of variable definition
        description (str): Description of variable's purpose
        values (list): Optional list of suggested values for this variable
        expandable (bool): True if the variable should be expanded, False if not.
        track_used (bool): True if the variable should be tracked as used,
                           False if not. Can help with allowing lists without vectorizing
        when (list | None): List of when conditions to apply to directive
    """

    def _define_package_manager_variable(pm):
        ramble.language.shared_language.variable(
            name,
            default,
            description=description,
            values=values,
            expandable=expandable,
            track_used=track_used,
            when=when,
            error_context="package_manager_variable",
            **kwargs,
        )(pm)

    return _define_package_manager_variable


@package_manager_directive("class_families")
def package_manager_family(*names: str, **kwargs):
    """Add a new family to this package manager

    Args:
        name (str): Name of family to apply to this package manager
    """

    def _define_package_manager_family(pm):
        for name in names:
            pm.class_families[name] = True

    return _define_package_manager_family
