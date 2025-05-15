# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from typing import Optional

import ramble.language.shared_language


class WorkflowManagerMeta(ramble.language.shared_language.SharedMeta):
    _directive_names = set()
    _directives_to_be_executed = []


workflow_manager_directive = WorkflowManagerMeta.directive


@workflow_manager_directive(dicts=())
def workflow_manager_variable(
    name: str,
    default,
    description: str,
    values: Optional[list] = None,
    when=None,
    **kwargs,
):
    """Define a variable for this wm
    Args:
        name: Name of variable
        default: Default value if the variable is not defined
        description: Description of the variable
        values: Optional list of suggested values for this variable
        when (list | None): List of when conditions to apply to directive
    """

    def _define_wm_variable(wm):
        import ramble.workload

        when_list = ramble.language.language_helpers.build_when_list(
            when, wm, name, "workflow_manager_variable"
        )

        wm.object_variables.append(
            ramble.workload.WorkloadVariable(
                name,
                default=default,
                description=description,
                values=values,
                when=when_list,
            )
        )

    return _define_wm_variable


@workflow_manager_directive(dicts=())
def workflow_manager_family(*names: str, **kwargs):
    """Add a new family to this workflow manager

    Args:
        name (str): Name of family to apply to this workflow manager
    """

    def _define_workflow_manager_family(wm):
        families_from_base = getattr(wm, "families", [])
        wm.families = list(sorted(set(families_from_base + list(names))))

    return _define_workflow_manager_family
