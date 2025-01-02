# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for mirrors.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/mirrors.py
   :lines: 13-
"""


#: Properties for inclusion in other schemas
properties = {
    "mirrors": {
        "type": "object",
        "default": {},
        "additionalProperties": False,
        "patternProperties": {
            r"\w[\w-]*": {
                "anyOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "required": ["fetch", "push"],
                        "properties": {
                            "fetch": {"type": ["string", "object"]},
                            "push": {"type": ["string", "object"]},
                        },
                    },
                ]
            },
        },
    },
}


#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Ramble mirror configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
