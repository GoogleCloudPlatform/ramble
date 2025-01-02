# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for package_manager_repos.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/package_manager_repos.py
   :lines: 13-
"""


#: Properties for inclusion in other schemas
properties = {
    "package_manager_repos": {
        "type": "array",
        "default": [],
        "items": {"type": "string"},
    },
}


#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble package manager repository configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
