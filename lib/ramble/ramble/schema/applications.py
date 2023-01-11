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

import ramble.schema.licenses

string_or_num = {
    'anyOf': [
        {'type': 'string'},
        {'type': 'number'}
    ]
}

array_or_scalar_of_strings_or_nums = {
    'anyOf': [
        {
            'type': 'array',
            'default': [],
            'items': string_or_num,
        },
        string_or_num
    ]
}

variables_def = {
    'type': 'object',
    'default': {},
    'properties': {},
    'additionalProperties': array_or_scalar_of_strings_or_nums
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


#: Properties for inclusion in other schemas
applications_schema = {
    'applications': {
        'type': 'object',
        'default': {},
        'properties': {},
        'additionalProperties': {
            'type': 'object',
            'default': '{}',
            'additionalProperties': {
                'variables': variables_def,
                'env-vars': ramble.schema.licenses.env_var_actions
            },
            'properties': {
                'workloads': {
                    'type': 'object',
                    'default': {},
                    'properties': {},
                    'additionalProperties': {
                        'type': 'object',
                        'default': {},
                        'additionalProperties': {
                            'variables': variables_def,
                            'env-vars': ramble.schema.licenses.env_var_actions
                        },
                        'properties': {
                            'experiments': {
                                'type': 'object',
                                'default': {},
                                'properties': {},
                                'additionalProperties': {
                                    'type': 'object',
                                    'default': {},
                                    'additionalProperties': {
                                        'variables': variables_def,
                                        'matrix': matrix_def,
                                        'matrices': matrices_def,
                                        'env-vars': ramble.schema.licenses.env_var_actions
                                    },
                                    'properties': {}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

#: Full schema with metadata
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'Ramble application configuration file schema',
    'type': 'object',
    'additionalProperties': False,
    'properties': applications_schema
}
