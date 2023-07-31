# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for application specific experiment configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/applications.py
   :lines: 12-
"""  # noqa E501

from llnl.util.lang import union_dicts
from ramble.schema.success_criteria import success_list_def

import ramble.schema.env_vars
import ramble.schema.internals
import ramble.schema.types
import ramble.schema.variables
import ramble.schema.success_criteria
import ramble.schema.licenses
import ramble.schema.modifiers


zip_def = {
    'type': 'array',
    'default': [],
    'items': {'type': 'string'}
}

zips_def = {
    'type': 'object',
    'default': {},
    'properties': {},
    'additionalProperties': zip_def
}

matrix_def = {
    'type': 'array',
    'default': [],
    'items': {'type': 'string'}
}

matrices_def = {
    'type': 'array',
    'default': [],
    'items': {
        'anyOf': [
            matrix_def,
            {
                'type': 'object',
                'default': {},
                'properties': {},
                'additionalProperties': matrix_def
            }
        ]
    }
}

chained_experiment_def = {
    'type': 'array',
    'default': [],
    'items': {
        'type': 'object',
        'default': {},
        'properties': union_dicts(
            {
                'name': {'type': 'string'},
                'command': {'type': 'string'},
                'order': {'type': 'string'},
            },
            ramble.schema.variables.properties
        ),
        'additionalProperties': False
    }
}

sub_props = union_dicts(
    ramble.schema.variables.properties,
    ramble.schema.success_criteria.properties,
    ramble.schema.env_vars.properties,
    ramble.schema.internals.properties,
    ramble.schema.modifiers.properties,
    {
        'chained_experiments': chained_experiment_def,
        'template': {'type': 'boolean'},
    }
)

#: Properties for inclusion in other schemas
properties = {
    'applications': {
        'type': 'object',
        'default': {},
        'properties': {},
        'additionalProperties': {
            'type': 'object',
            'default': '{}',
            'additionalProperties': False,
            'properties': union_dicts(
                sub_props,
                {
                    'workloads': {
                        'type': 'object',
                        'default': {},
                        'properties': {},
                        'additionalProperties': {
                            'type': 'object',
                            'default': {},
                            'additionalProperties': False,
                            'properties': union_dicts(
                                sub_props,
                                {
                                    'experiments': {
                                        'type': 'object',
                                        'default': {},
                                        'properties': {},
                                        'additionalProperties': {
                                            'type': 'object',
                                            'default': {},
                                            'additionalProperties': False,
                                            'properties': union_dicts(
                                                sub_props,
                                                {
                                                    'zips': zips_def,
                                                    'matrix': matrix_def,
                                                    'matrices': matrices_def,
                                                    'success_criteria': success_list_def,
                                                }
                                            )
                                        }
                                    }
                                }
                            )
                        }
                    }
                }
            )
        }
    }
}

#: Full schema with metadata
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'Ramble application configuration file schema',
    'type': 'object',
    'additionalProperties': False,
    'properties': properties
}
