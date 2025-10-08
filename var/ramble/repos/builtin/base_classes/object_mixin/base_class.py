# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
from html import escape

from ramble.repository import ObjectTypes, get_base_class
from ramble.util import format


class ObjectMixin:
    """A mixin class for Ramble objects"""

    def __str__(self):
        return self.name

    def copy(self):
        """Generic copy method for Ramble objects."""
        new_copy = type(self)(self._file_path)
        if hasattr(self, "_verbosity"):
            new_copy._verbosity = self._verbosity
        return new_copy

    def all_pipeline_phases(self, pipeline):
        """Iterator over all phases within a specified pipeline

        Iterate over all phases (and their graph nodes) within a pipeline.

        Args:
            pipeline (str): Name of pipeline to extract phases for

        Yields:
            phase_name (str): Name of phase
            phase_note (ramble.util.graph.GraphNode): Object representing a
                node in the phase graph
        """
        if pipeline in self.phase_definitions:
            yield from self.phase_definitions[pipeline].items()

    def _get_app_inst(self):
        # This helper gets the app_inst for different object types
        if hasattr(self, "app_inst"):
            return self.app_inst
        return self

    def _get_object_type(self):
        ApplicationBase = get_base_class("application-base")
        PackageManagerBase = get_base_class("package-manager-base")
        WorkflowManagerBase = get_base_class("workflow-manager-base")
        ModifierBase = get_base_class("modifier-base")

        if isinstance(self, ApplicationBase):
            return ObjectTypes.applications
        elif isinstance(self, PackageManagerBase):
            return ObjectTypes.package_managers
        elif isinstance(self, WorkflowManagerBase):
            return ObjectTypes.workflow_managers
        elif isinstance(self, ModifierBase):
            return ObjectTypes.modifiers
        return None

    def satisfy_when(self, when_key, variant_set=None):
        app_inst = self._get_app_inst()
        experiment_variants = self.experiment_variants()
        return app_inst.expander.satisfies(when_key, experiment_variants)

    def experiment_variants(self, include_modifier=None):
        """Construct a VariantSet for this experiment.

        Apply some merging logic to VariantSet combination, in order to
        provide scoped variant definitions.

        Args:
            include_modifier (ModifierBase): A single modifier to merge in to resulting set

        Returns:
            VariantSet: Merged variants for the experiment.
        """
        app_inst = self._get_app_inst()

        self_type = self._get_object_type()
        new_set = self.object_variants.copy()

        exclude_types = [self_type]

        if include_modifier is not None:
            exclude_types.append(ObjectTypes.modifiers)
            new_set.merge_variants(include_modifier.object_variants)

        for _, obj in app_inst._objects(exclude_types=exclude_types):
            new_set.merge_variants(obj.object_variants)

        return new_set

    @property
    def required_variables(self):
        """Get all the required variables based on the mode and when conditions."""
        if not self.required_vars:
            return {}

        return {
            var_name: {k: var_props[k] for k in var_props.keys() - {"when"}}
            for var_name, var_props in self.required_vars.items()
            if self.satisfy_when(var_props["when"])
        }

    @property
    def selected_variables(self):
        """Extract all variables which would be included based
        on the current variants.

        Returns:
            (dict) Keys are variable names, values are variable instances
        """
        return {
            var.name: var
            for when_key, var_list in self.object_variables.items()
            if self.satisfy_when(when_key)
            for var in var_list
        }

    @property
    def selected_environment_variables(self):
        """Extract all environment variables which would be included based
        on the current variants.

        Returns:
            (dict) Keys are environment variable names, values are environment
            variable instances
        """
        return {
            env_var.name: env_var
            for when_key, env_var_list in self.object_environment_variables.items()
            if self.satisfy_when(when_key)
            for env_var in env_var_list
        }

    def add_inmem_fom_value(self, fom_map_key, value):
        """Add an in-memory FOM value"""
        app_inst = self._get_app_inst()
        app_inst.add_inmem_fom_value(fom_map_key, value)

    def _github_url(self, obj_def):
        """Link to an object file on github."""
        base_url = "https://github.com/GoogleCloudPlatform/ramble/blob/develop/var/ramble/repos/builtin"
        return f'{base_url}/{obj_def["dir_name"]}/{self.name}/{obj_def["file_name"]}'

    def to_html_docs(self, out, obj_def):
        """Writes HTML documentation for this object."""
        out.write('<dl class="docutils">\n')

        out.write(f'<dt>Ramble {obj_def["dir_name"]}:</dt>\n')
        out.write('<dd><ul class="first last simple">\n')
        out.write(
            "<li>"
            '<a class="reference external" '
            f'href="{self._github_url(obj_def)}">'
            f'{self.name}/{obj_def["file_name"]}</a>'
            "</li>\n"
        )
        out.write("</ul></dd>\n")

        out.write("<dt>Description:</dt>\n")
        out.write("<dd>\n")
        out.write(escape(format.format_doc(self.__doc__, indent=2), True))
        out.write("\n")
        out.write("</dd>\n")

        self._format_docs_details(out)

        out.write("</dl>\n")

    def _format_docs_details(self, _out):
        """Hook for objects to add extra documentation."""
