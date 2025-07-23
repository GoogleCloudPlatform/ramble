# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for workflow manager definitions"""

from typing import List

import ramble.definitions.families
import ramble.util.class_attributes
import ramble.util.directives
import ramble.variants
from ramble.expander import ExpanderError
from ramble.language.shared_language import SharedMeta
from ramble.language.workflow_manager_language import (
    WorkflowManagerMeta,
    workflow_manager_variable,
)
from ramble.util import format
from ramble.util.naming import NS_SEPARATOR


class WorkflowManagerBase(metaclass=WorkflowManagerMeta):
    name = None
    origin_type = "workflow_manager"
    _builtin_name = NS_SEPARATOR.join(
        ("workflow_manager_builtin", "{obj_name}", "{name}")
    )
    _language_classes = [WorkflowManagerMeta, SharedMeta]
    _pipelines = [
        "analyze",
        "setup",
        "execute",
    ]
    maintainers: List[str] = []
    tags: List[str] = []

    workflow_manager_variable(
        "workflow_banner",
        default="",
        description="Banner to describe the workflow within execution templates",
    )

    workflow_manager_variable(
        "workflow_pragmas",
        default="",
        description="Pragmas to apply within execution templates for the workflow",
    )

    workflow_manager_variable(
        "workflow_hostfile_cmd",
        default="",
        description="Hostfile command to apply within execution templates for the workflow",
    )

    workflow_manager_variable(
        "hostfile",
        default="{experiment_run_dir}/hostfile",
        description="Default hostfile path",
    )

    def __init__(self, file_path):
        super().__init__()

        self.object_variants = ramble.variants.VariantSet()
        for var_args in self.class_variants.values():
            self.object_variants.default_variant(**var_args)

        if getattr(self, "families", None) is None:
            self.families = ramble.definitions.families.Families(
                self.origin_type, list(self.class_families.keys())
            )

        ramble.util.class_attributes.convert_class_attributes(self)

        self._file_path = file_path

        ramble.util.directives.define_directive_methods(self)

        self.object_variants.default_variant(
            self.origin_type,
            default=self.name,
            description="Name of workflow manager for an experiment",
        )

        for family in self.families:
            self.object_variants.multi_value_variant(
                self.families.family_type,
                value=family,
            )

        self.app_inst = None
        self.runner = None

    def set_application(self, app_inst):
        """Set a reference to the associated app_inst"""
        self.app_inst = app_inst

    def get_status(self, workspace):
        """Return status of a given job"""
        return None

    def conditional_expand(self, templates):
        """Return a (potentially empty) list of expanded strings

        Args:
            templates: A list of templates to expand.
                If the template cannot be fully expanded, it's skipped.
        Returns:
            A list of expanded strings
        """
        expander = self.app_inst.expander
        expanded = []
        for tpl in templates:
            try:
                rendered = expander.expand_var(tpl, allow_passthrough=False)
                if rendered:
                    expanded.append(rendered)
            except ExpanderError:
                # Skip a particular entry if any of the vars are not defined
                continue
        return expanded

    def template_render_vars(self):
        """Define variables to be used in template rendering"""
        return {}

    def copy(self):
        """Deep copy a workflow manager instance"""
        new_copy = type(self)(self._file_path)

        return new_copy

    def __str__(self):
        return self.name

    def selected_variables(self):
        """Extract all variables which would be included based
        on the current variants.

        Returns:
            (dict) Keys are variable names, values are variable instances
        """

        all_vars = {}
        for when_key, var_list in self.object_variables.items():
            if not self.app_inst.expander.satisfies(
                when_key, self.app_inst.object_variants
            ):
                continue

            for var in var_list:
                all_vars[var.name] = var
        return all_vars

    def selected_environment_variables(self):
        """Extract all environment variables which would be included based
        on the current variants.

        Returns:
            (dict) Keys are environment variable names, values are environment
            variable instances
        """

        all_env_vars = {}
        for (
            when_key,
            env_var_list,
        ) in self.object_environment_variables.items():
            if not self.app_inst.expander.satisfies(
                when_key, self.app_inst.object_variants
            ):
                continue

            for env_var in env_var_list:
                all_env_vars[env_var.name] = env_var
        return all_env_vars

    def format_doc(self, **kwargs):
        return format.format_doc(self.__doc__, **kwargs)

    def get_required_variables(self):
        """Get all the required variables based on the mode and when conditions."""
        required_vars = self.required_vars
        filtered_vars = {}
        if required_vars:
            for var_name, var_props in required_vars.items():
                if self.app_inst.expander.satisfies(
                    var_props["when"], self.app_inst.object_variants
                ):
                    filtered_vars[var_name] = {
                        # Exclude the extra when prop
                        k: var_props[k]
                        for k in var_props.keys() - {"when"}
                    }
        return filtered_vars
