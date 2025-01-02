# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for configuration merged into one file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/merged.py
   :lines: 14-
"""
from llnl.util.lang import union_dicts

import ramble.schema.applications
import ramble.schema.config
import ramble.schema.formatted_executables
import ramble.schema.licenses
import ramble.schema.repos
import ramble.schema.spack  # DEPRECATED: Remove when spack is removed
import ramble.schema.software
import ramble.schema.success_criteria
import ramble.schema.variables
import ramble.schema.variants
import ramble.schema.env_vars
import ramble.schema.internals
import ramble.schema.modifiers
import ramble.schema.zips

#: Properties for inclusion in other schemas
properties = union_dicts(
    ramble.schema.applications.properties,
    ramble.schema.config.properties,
    ramble.schema.formatted_executables.properties,
    ramble.schema.licenses.properties,
    ramble.schema.repos.properties,
    ramble.schema.spack.properties,  # DEPRECATED: Remove when spack is removed
    ramble.schema.software.properties,
    ramble.schema.success_criteria.properties,
    ramble.schema.variables.properties,
    ramble.schema.variants.properties,
    ramble.schema.env_vars.properties,
    ramble.schema.internals.properties,
    ramble.schema.modifiers.properties,
    ramble.schema.zips.properties,
)

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Ramble merged configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
