# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for success criteria configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/success_criteria.py
   :lines: 12-
"""  # noqa E501


success_criteria_def = {
    "type": "object",
    "default": {},
    "properties": {
        "name": {"type": "string"},
        "mode": {"type": "string"},
        "match": {"type": "string", "default": None},
        "file": {"type": "string", "default": None},
        "fom_name": {"type": "string", "default": None},
        "fom_context": {"type": "string", "default": None},
        "formula": {"type": "string", "default": None},
        "anti_match": {"type": "string", "default": None},
    },
    "additionalProperties": False,
}

success_list_def = {"type": "array", "default": [], "items": success_criteria_def}


#: Properties for inclusion in other schemas
properties = {"success_criteria": success_list_def}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble success criteria configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
