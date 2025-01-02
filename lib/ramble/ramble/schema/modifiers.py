# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for modifiers configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/modifiers.py
   :lines: 12-
"""  # noqa E501

section_name = "modifiers"

#: Properties for inclusion in other schemas
properties = {
    section_name: {
        "type": "array",
        "default": [],
        "items": {
            "type": "object",
            "default": {},
            "properties": {
                "name": {"type": "string"},
                "mode": {"type": "string"},
                "on_executable": {"type": "array", "default": [], "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
    }
}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble application configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
