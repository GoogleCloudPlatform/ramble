# Copyright 2022-2023 Google LLC
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

import ramble.schema.variables
import ramble.schema.applications

#: Properties for inclusion in other schemas
properties = {
    'spack': {
        'type': 'object',
        'properties': {
            'concretized': {
                'type': 'boolean',
                'default': False
            },
            'variables': ramble.schema.variables.variables_def,
            'packages': {
                'type': 'object',
                'additionalProperties': {
                    'type': 'object',
                    'properties': {
                        'spack_spec': {'type': 'string'},
                        'compiler_spec': {
                            'type': 'string',
                            'default': None,
                        },
                        'compiler': {
                            'type': 'string',
                            'default': None,
                        },
                        'variables': ramble.schema.variables.variables_def,
                        'zips': ramble.schema.applications.zips_def,
                        'matrix': ramble.schema.applications.matrix_def,
                        'matrices': ramble.schema.applications.matrices_def,
                        'exclude': ramble.schema.applications.exclude_def,
                    },
                    'additionalProperties': False,
                    'default': {}
                },
            },
            'environments': {
                'type': 'object',
                'properties': {},
                'default': {},
                'additionalProperties': {
                    'type': 'object',
                    'properties': {
                        'external_spack_env': {
                            'type': 'string',
                            'default': None,
                        },
                        'packages': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'default': []
                        },
                        'variables': ramble.schema.variables.variables_def,
                        'zips': ramble.schema.applications.zips_def,
                        'matrix': ramble.schema.applications.matrix_def,
                        'matrices': ramble.schema.applications.matrices_def,
                        'exclude': ramble.schema.applications.exclude_def,
                    },
                    'additionalProperties': False,
                    'default': {}
                }
            }
        },
        'default': {},
        'additionalProperties': False,
    }
}


#: Full schema with metadata
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'Spack software configuration file schema',
    'type': 'object',
    'additionalProperties': False,
    'properties': properties,
}
