# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for filter_groups configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/filter_groups.py
   :lines: 12-
"""

filter_groups_def = {
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "properties": {
            "where": {
                "type": "array",
                "items": {"type": "string"},
            },
            "exclude_where": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "additionalProperties": False,
    },
}

properties = {"filter_groups": filter_groups_def}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Ramble filter groups configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
