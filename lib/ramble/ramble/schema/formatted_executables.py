# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for defining variables representing the formatted merging of executables

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/formatted_executables.py
   :lines: 12-
"""  # noqa E501

#: Properties for inclusion in other schemas
properties = {
    "formatted_executables": {
        "type": "object",
        "default": {},
        "properties": {},
        "additionalProperties": {
            "type": "object",
            "default": {},
            "additionalProperties": False,
            "properties": {
                "prefix": {"type": "string", "default": ""},
                "indentation": {"type": "number", "default": 0},
                "join_separator": {"type": "string", "default": "\n"},
                "commands": {
                    "type": "array",
                    "default": ["{unformatted_command}"],
                    "items": {
                        "type": "string",
                    },
                },
            },
        },
    }
}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble formatted executables configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
