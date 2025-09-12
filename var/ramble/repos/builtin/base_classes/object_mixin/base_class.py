# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.util import format


class ObjectMixin:
    """A mixin class for Ramble objects"""

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

    def format_doc(self, **kwargs):
        """Doc formatting for Sphinx"""
        return format.format_doc(self.__doc__, **kwargs)

    def add_inmem_fom_value(self, fom_map_key, value):
        """Add an in-memory FOM value"""
        app_inst = self._get_app_inst()
        app_inst.add_inmem_fom_value(fom_map_key, value)
