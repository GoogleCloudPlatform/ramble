# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
from html import escape

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

    def satisfy_when(self, when_key):
        app_inst = self._get_app_inst()
        return app_inst.expander.satisfies(when_key, app_inst.object_variants)

    @property
    def required_variables(self):
        """Get all the required variables based on the mode and when conditions."""
        required_vars = self.required_vars
        filtered_vars = {}
        if required_vars:
            for var_name, var_props in required_vars.items():
                if self.satisfy_when(var_props["when"]):
                    filtered_vars[var_name] = {
                        # Exclude the extra when prop
                        k: var_props[k]
                        for k in var_props.keys() - {"when"}
                    }
        return filtered_vars

    @property
    def selected_variables(self):
        """Extract all variables which would be included based
        on the current variants.

        Returns:
            (dict) Keys are variable names, values are variable instances
        """

        selected_vars = {}
        for when_key, var_list in self.object_variables.items():
            if not self.satisfy_when(when_key):
                continue

            for var in var_list:
                selected_vars[var.name] = var
        return selected_vars

    @property
    def selected_environment_variables(self):
        """Extract all environment variables which would be included based
        on the current variants.

        Returns:
            (dict) Keys are environment variable names, values are environment
            variable instances
        """

        selected_env_vars = {}
        for (
            when_key,
            env_var_list,
        ) in self.object_environment_variables.items():
            if not self.satisfy_when(when_key):
                continue

            for env_var in env_var_list:
                selected_env_vars[env_var.name] = env_var

        return selected_env_vars

    def add_inmem_fom_value(self, fom_map_key, value):
        """Add an in-memory FOM value"""
        app_inst = self._get_app_inst()
        app_inst.add_inmem_fom_value(fom_map_key, value)

    def _github_url(self, obj_def):
        """Link to an object file on github."""
        return (
            "https://github.com/GoogleCloudPlatform/ramble/blob/develop/var/ramble/repos/builtin/"
            + f'{obj_def["dir_name"]}/'
            + self.name
            + f'/{obj_def["file_name"]}'
        )

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
