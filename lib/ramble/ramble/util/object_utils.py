# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Module for providing utils related to Ramble objects."""

import fnmatch
import re

import ramble.repository


def filter_by_name(glob_patterns, search_description, obj_type):
    """
    Filters the sequence of object names by the given glob patterns.

    Args:
        glob_patterns: patterns to match against object names
        search_description: whether to search inside object descriptions
        obj_type: type of the Ramble objects to search for

    Returns:
        filtered and sorted list of object names
    """
    obj_names = set(ramble.repository.all_object_names(obj_type))
    if glob_patterns:
        patts = []
        for f in glob_patterns:
            if "*" not in f and "?" not in f:
                r = fnmatch.translate("*" + f + "*")
            else:
                r = fnmatch.translate(f)
            rc = re.compile(r, flags=re.IGNORECASE)
            patts.append(rc)
        obj_names = [
            obj_name
            for obj_name in obj_names
            if any(_match(obj_name, patt, search_description, obj_type) for patt in patts)
        ]
    return sorted(obj_names, key=lambda s: s.lower())


def _match(obj_name, pattern, search_description, obj_type):
    if pattern.match(obj_name):
        return True
    if not search_description:
        return False
    obj = ramble.repository.get(obj_name, object_type=obj_type)
    if obj.__doc__:
        return pattern.match(obj.__doc__)
    return False
