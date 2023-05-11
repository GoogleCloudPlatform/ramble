# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for configuration merged into one file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/merged.py
   :lines: 39-
"""
from llnl.util.lang import union_dicts

import ramble.schema.applications
import ramble.schema.config
import ramble.schema.repos
import ramble.schema.spack
import ramble.schema.success_criteria
import ramble.schema.variables
import ramble.schema.env_vars

#: Properties for inclusion in other schemas
properties = union_dicts(
    ramble.schema.applications.properties,
    ramble.schema.config.properties,
    ramble.schema.repos.properties,
    ramble.schema.spack.properties,
    ramble.schema.success_criteria.properties,
    ramble.schema.variables.properties,
    ramble.schema.env_vars.properties,
)

#: Full schema with metadata
schema = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    'title': 'Ramble merged configuration file schema',
    'type': 'object',
    'additionalProperties': False,
    'properties': properties,
}
