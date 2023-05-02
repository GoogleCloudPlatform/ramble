# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for workspace.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/workspace.py
   :lines: 12-
"""  # noqa E501

import spack.schema.env
import ramble.schema.applications

env_properties = spack.schema.env.schema['patternProperties']
spec_properties = env_properties['^env|spack$']

applications_schema = ramble.schema.applications.schema
applications_properties = applications_schema['properties']['applications']
app_addProps = applications_properties['additionalProperties']

spec_def = {
    'type': 'object',
    'properties': {},
    'default': {},
    'additionalProperties': {
        'type': 'object',
        'default': {},
        'properties': {
            'base': {
                'type': 'string',
                'default': ''
            }
        },
        'additionalProperties': {
            'base': {'type': 'string'},
            'version': {'type': 'string'},
            'variants': {'type': 'string'},
            'compiler': {'type': 'string'},
            'mpi': {'type': 'string'},
            'target': {'type': 'string'},
            'arch': {'type': 'string'},
            'dependencies': {
                'type': 'array',
                'default': [],
                'elements': {'type': 'string'}
            }
        }
    }
}


keys = ('ramble', 'workspace')

#: Properties for inclusion in other schemas
properties = {
    'ramble': {
        'type': 'object',
        'default': {},
        'properties': {
            'software_variables': {
                'type': 'object',
                'additionalProperties': {'type': 'string'},
            },
            'variables': ramble.schema.applications.variables_def,
            'internals': ramble.schema.applications.internals_def,
            'success_criteria': ramble.schema.applications.success_list_def,
            'include': {
                'type': 'array',
                'default': [],
                'items': {'type': 'string'},
            },
            'applications': {
                'type': applications_properties['type'],
                'default': applications_properties['default'],
                'properties': applications_properties['properties'],
                'additionalProperties': app_addProps
            }
        },
        'additionalProperties': {
            'application_directories': {
                'type': 'array',
                'default': [],
                'items': {
                    'type': 'string'
                }
            }
        }
    },
    'spack': {
        'type': 'object',
        'properties': {
            'concretized': {
                'type': 'boolean',
                'default': False
            }
        },
        'default': {},
        'additionalProperties': {
            'compilers': spec_def,
            'mpi_libraries': spec_def,
            'applications': {
                'type': 'object',
                'default': {},
                'properties': {},
                'additionalProperties': spec_def
            }
        }
    }
}


#: Full schema with metadata
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'Ramble workspace configuration file schema',
    'type': 'object',
    'additionalProperties': False,
    'properties': properties,
}
