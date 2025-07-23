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

    def get_app_inst(self):
        if hasattr(self, "app_inst"):
            return self.app_inst
        return self

    def get_required_variables(self):
        """Get all the required variables based on the mode and when conditions."""
        app_inst = self.get_app_inst()
        required_vars = self.required_vars
        filtered_vars = {}
        if required_vars:
            for var_name, var_props in required_vars.items():
                if app_inst.expander.satisfies(var_props["when"], app_inst.object_variants):
                    filtered_vars[var_name] = {
                        # Exclude the extra when prop
                        k: var_props[k]
                        for k in var_props.keys() - {"when"}
                    }
        return filtered_vars

    def format_doc(self, **kwargs):
        return format.format_doc(self.__doc__, **kwargs)
