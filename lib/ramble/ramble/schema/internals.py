# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for internals configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/internals.py
   :lines: 12-
"""  # noqa E501

from llnl.util.lang import union_dicts

import ramble.schema.types
import ramble.schema.variables
from ramble.util.output_capture import OUTPUT_CAPTURE


custom_executables_def = {
    "type": "object",
    "properties": {},
    "additionalProperties": {
        "type": "object",
        "default": {
            "template": [],
            "use_mpi": False,
            "redirect": "{log_file}",
            "variables": {},
            "output_capture": OUTPUT_CAPTURE.DEFAULT,
        },
        "properties": union_dicts(
            {
                "template": ramble.schema.types.array_or_scalar_of_strings_or_nums,
                "use_mpi": {"type": "boolean"},
                "redirect": ramble.schema.types.string_or_num,
            },
            ramble.schema.variables.properties,
        ),
    },
    "default": {},
}

executables_def = ramble.schema.types.array_of_strings_or_nums

executable_injection_def = {
    "type": "array",
    "default": [],
    "items": {
        "type": "object",
        "default": {},
        "properties": {
            "name": {"type": "string"},
            "order": {
                "type": "string",
                "default": "after",
            },
        },
        "additionalProperties": {"relative_to": {"type": "string"}},
    },
}

internals_def = {
    "type": "object",
    "default": {},
    "properties": {
        "custom_executables": custom_executables_def,
        "executables": executables_def,
        "executable_injection": executable_injection_def,
    },
    "additionalProperties": False,
}

#: Properties for inclusion in other schemas
properties = {"internals": internals_def}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble internals configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
