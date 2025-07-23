# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# This file contains utilities useful for various Ramble objects.


def get_required_variables(obj_inst, app_inst=None):
    """Get all the required variables based on the mode and when conditions."""
    if app_inst is None:
        app_inst = obj_inst
    required_vars = obj_inst.required_vars
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
