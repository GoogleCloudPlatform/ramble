# Copyright 2022-2025 The Ramble Authors
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
        obj (Object): Input object instance to convert attributes in
    """

    if hasattr(obj, "_directive_names"):
        dir_set = dir(obj)
        var_set = vars(obj)
        for attr in obj._directive_names:
            if attr in dir_set and attr not in var_set:
                inst_val = getattr(obj, attr).copy()
                setattr(obj, attr, inst_val)
