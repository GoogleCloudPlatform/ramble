# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for variables configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/variables.py
   :lines: 12-
"""  # noqa E501

variables_def = {
    "type": ["object", "null"],
    "default": {},
    "properties": {},
    "additionalProperties": True,
}

properties = {"variables": variables_def}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble variables configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
