# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
"""Schema for bootstrap.yaml configuration file."""

#: Schema of a single source
_source_schema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'metadata': {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['name', 'metadata']
}

properties = {
    'bootstrap': {
        'type': 'object',
        'properties': {
            'enable': {'type': 'boolean'},
            'root': {
                'type': 'string'
            },
            'sources': {
                'type': 'array',
                'items': _source_schema
            },
            'trusted': {
                'type': 'object',
                'patternProperties': {r'\w[\w-]*': {'type': 'boolean'}}
            }
        }
    }
}

#: Full schema with metadata
schema = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    'title': 'Spack bootstrap configuration file schema',
    'type': 'object',
    'additionalProperties': False,
    'properties': properties,
}
