# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for licenses.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/licenses.py
   :lines: 12-
"""  # noqa E501

import spack.schema.environment

dictionary_of_strings_or_num = spack.schema.environment.dictionary_of_strings_or_num
array_of_strings_or_num = spack.schema.environment.array_of_strings_or_num

env_var_actions = {
    "set": dictionary_of_strings_or_num,
    "append": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "var-separator": {"type": "string"},
                "vars": dictionary_of_strings_or_num,
                "paths": dictionary_of_strings_or_num,
            },
            "additionalProperties": {},
        },
    },
    "prepend": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "paths": dictionary_of_strings_or_num,
            },
            "additionalProperties": {},
        },
    },
    "unset": array_of_strings_or_num,
}

#: Properties for inclusion in other schemas
properties = {
    "licenses": {
        "type": "object",
        "default": {},
        "properties": {},
        "additionalProperties": {
            "type": "object",
            "default": {},
            "additionalProperties": False,
            "properties": env_var_actions,
        },
    }
}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble licenses configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
