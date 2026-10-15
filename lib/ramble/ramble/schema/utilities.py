# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for utilities.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/utilities.py
   :lines: 12-
"""

#: Properties for inclusion in other schemas
properties = {
    "utilities": {
        "type": "object",
        "default": {},
        "patternProperties": {
            r"[\w\d\-_\.]+": {
                "type": "object",
                "default": {},
                "additionalProperties": True,
            }
        },
    }
}


#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble external dependencies configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
