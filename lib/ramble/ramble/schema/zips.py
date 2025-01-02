# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for variable zips configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/zips.py
   :lines: 12-
"""  # noqa E501


zip_def = {"type": "array", "default": [], "items": {"type": "string"}}

zips_def = {"type": "object", "default": {}, "properties": {}, "additionalProperties": zip_def}

#: Properties for inclusion in other schemas
properties = {
    "zips": zips_def,
}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble zips configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
