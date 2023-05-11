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
import ramble.schema.types


variables_def = {
    'type': ['object', 'null'],
    'default': {},
    'properties': {},
    'additionalProperties': ramble.schema.types.array_or_scalar_of_strings_or_nums
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

success_criteria_def = {
    'type': 'object',
    'default': {},
    'properties': {
        'name': {'type': 'string'},
        'mode': {'type': 'string'},
        'match': {'type': 'string'},
        'file': {'type': 'string'}
    },
    'additionalProperties': False,
}

success_list_def = {
    'type': 'array',
    'default': [],
    'items': success_criteria_def
}

custom_executables_def = {
    'type': 'object',
    'properties': {},
    'additionalProperties': {
        'type': 'object',
        'default': {
            'template': [],
            'use_mpi': False,
            'redirect': '{log_file}',
            'output_capture': ramble.schema.types.OUTPUT.DEFAULT
        },
        'properties': {
            'template': ramble.schema.types.array_or_scalar_of_strings_or_nums,
            'use_mpi': {'type': 'boolean'},
            'redirect': ramble.schema.types.string_or_num,
        }
    },
    'default': {},
}

executables_def = ramble.schema.types.array_of_strings_or_nums

internals_def = {
    'type': 'object',
    'default': {},
    'properties': {
        'custom_executables': custom_executables_def,
        'executables': executables_def,
    },
    'additionalProperties': False
}

chained_experiment_def = {
    'type': 'array',
    'default': [],
    'items': {
        'type': 'object',
        'default': {},
        'properties': {
            'name': {'type': 'string'},
            'command': {'type': 'string'},
            'order': {'type': 'string'},
            'variables': variables_def,
        },
        'additionalProperties': False
    }
}

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
            'properties': {
                'variables': variables_def,
                'env-vars': ramble.schema.licenses.env_var_actions,
                'internals': internals_def,
                'success_criteria': success_list_def,
                'chained_experiments': chained_experiment_def,
                'template': {'type': 'boolean'},
                'workloads': {
                    'type': 'object',
                    'default': {},
                    'properties': {},
                    'additionalProperties': {
                        'type': 'object',
                        'default': {},
                        'additionalProperties': False,
                        'properties': {
                            'variables': variables_def,
                            'env-vars': ramble.schema.licenses.env_var_actions,
                            'internals': internals_def,
                            'success_criteria': success_list_def,
                            'chained_experiments': chained_experiment_def,
                            'template': {'type': 'boolean'},
                            'experiments': {
                                'type': 'object',
                                'default': {},
                                'properties': {},
                                'additionalProperties': {
                                    'type': 'object',
                                    'default': {},
                                    'additionalProperties': False,
                                    'properties': {
                                        'variables': variables_def,
                                        'matrix': matrix_def,
                                        'matrices': matrices_def,
                                        'env-vars': ramble.schema.licenses.env_var_actions,
                                        'internals': internals_def,
                                        'success_criteria': success_list_def,
                                        'chained_experiments': chained_experiment_def,
                                        'template': {'type': 'boolean'},
                                    }
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
    'properties': properties
}
