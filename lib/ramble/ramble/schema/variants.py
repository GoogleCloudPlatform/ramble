# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for variants configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/variants.py
   :lines: 12-
"""  # noqa E501

variants_def = {
    "type": ["object", "null"],
    "default": {},
    "properties": {},
    "additionalProperties": True,
}

properties = {"variants": variants_def}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble variants configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
