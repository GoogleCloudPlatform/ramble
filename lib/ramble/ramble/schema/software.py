# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for software.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/software.py
   :lines: 12-
"""  # noqa E501

import ramble.namespace

namespace = ramble.namespace.namespace()


#: Properties for inclusion in other schemas
properties = {
    "software": {
        "type": "object",
        "properties": {
            "packages": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "pkg_spec": {"type": "string"},
                        "compiler_spec": {
                            "type": "string",
                            "default": None,
                        },
                        "compiler": {
                            "type": "string",
                            "default": None,
                        },
                    },
                    # Additional properties are of the form:
                    #    <pkg_manager_name>_pkg_spec:
                    #    <pkg_manager_name>_compiler_spec:
                    #    <pkg_manager_name>_compiler:
                    "additionalProperties": True,
                    "default": {},
                },
            },
            "environments": {
                "type": "object",
                "properties": {},
                "default": {},
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        namespace.external_env: {
                            "type": "string",
                            "default": None,
                        },
                        "packages": {"type": "array", "items": {"type": "string"}, "default": []},
                    },
                    "additionalProperties": {"type": "string"},
                    "default": {},
                },
            },
        },
        "default": {},
        "additionalProperties": False,
    }
}


#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Software configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
