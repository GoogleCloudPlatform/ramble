# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for config.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/config.py
   :lines: 15-
"""

import spack.schema.config

#: Properties for inclusion in other schemas
properties = {
    'config': {
        **spack.schema.config.properties['config']
    },
}

properties['config']['shell'] = {
    'type': 'string',
    'enum': ['sh', 'bash', 'csh', 'tcsh', 'fish']
}

#: Full schema with metadata
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'Ramble core configuration file schema',
    'type': 'object',
    'additionalProperties': False,
    'properties': properties,
}


def update(data):
    """Update the data in place to remove deprecated properties.

    Args:
        data (dict): dictionary to be updated

    Returns:
        True if data was changed, False otherwise
    """
    changed = False

    # There are no currently deprecated properties.
    # This is a stub to allow deprecated properties to be removed later, once
    # they exist.

    return changed
