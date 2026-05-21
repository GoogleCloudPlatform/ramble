# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def convert_class_attributes(obj):
    """Convert class attributes defined from directives to instance attributes
    Class attributes that are valid for conversion are stored in the _directive_names
    attribute.

    Args:
        obj (object): Input object instance to convert attributes in
    """

    if hasattr(obj, "_directive_names"):
        var_set = vars(obj)
        for attr in obj._directive_names:
            if attr not in var_set and hasattr(obj, attr):
                val = getattr(obj, attr)
                if hasattr(val, "copy"):
                    inst_val = val.copy()
                else:
                    inst_val = val
                setattr(obj, attr, inst_val)
