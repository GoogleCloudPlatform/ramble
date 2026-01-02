# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for workspace.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/workspace.py
   :lines: 12-
"""

from llnl.util.lang import union_dicts

import ramble.schema.merged

keys = ("ramble", "workspace")

#: Properties for inclusion in other schemas
properties = {
    "ramble": {
        "type": "object",
        "default": {},
        "properties": union_dicts(
            ramble.schema.merged.properties,
            {
                "include": {
                    "type": "array",
                    "default": [],
                    "items": {"type": "string"},
                },
            },
        ),
        "additionalProperties": False,
    },
}


#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble workspace configuration file schema",
    "type": "object",
    "properties": properties,
}
