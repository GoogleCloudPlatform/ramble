# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for spack.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/spack.py
   :lines: 12-
"""  # noqa E501

import ramble.namespace

namespace = ramble.namespace.namespace()


#: Properties for inclusion in other schemas
properties = {
    "spack": {
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
                    "additionalProperties": {"type": "string"},
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
                        "external_spack_env": {
                            "type": "string",
                            "default": None,
                        },
                        namespace.external_env: {
                            "type": "string",
                            "default": None,
                        },
                        "packages": {"type": "array", "items": {"type": "string"}, "default": []},
                    },
                    "additionalProperties": False,
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
    "title": "Spack software configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}


def update(data):
    changed = False

    pkg_keymap = {
        "spack_spec": "pkg_spec",
    }

    if "packages" in data:
        for pkg_name in data["packages"]:

            for key, newkey in pkg_keymap.items():
                if key in data["packages"][pkg_name] and newkey not in data["packages"][pkg_name]:
                    changed = True
                    data["packages"][pkg_name][newkey] = data["packages"][pkg_name][key]
                    del data["packages"][pkg_name][key]

    if "environments" in data:
        for env_name in data["environments"]:
            if "external_spack_env" in data["environments"][env_name]:
                changed = True
                data["environments"][env_name][namespace.external_env] = data["environments"][
                    env_name
                ]["external_spack_env"]
                del data["environments"][env_name]["external_spack_env"]

    return changed
