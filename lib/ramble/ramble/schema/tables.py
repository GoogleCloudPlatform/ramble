# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for the `tables` section of a ramble config."""

where_clause = {"type": "array", "items": {"type": "string"}}

column = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "expression": {"type": "string", "default": None},
        "figure_of_merit": {"type": "string", "default": None},
        "figure_of_merit_context": {"type": "string", "default": None},
        "figure_of_merit_origin_type": {"type": "string", "default": None},
        "where": where_clause,
    },
    "required": ["name"],
    "additionalProperties": False,
}

# TODO: Make key a table attribute that has to be an expression
properties = {
    "tables": {
        "type": "array",
        "default": [],
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "columns": {"type": "array", "items": column},
                "group_method": {"type": "string", "default": "max"},
                "group_by": {
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                    "default": None,
                },
                "sort_by": {
                    "type": ["string", "array"],
                    "items": {"type": "string"},
                    "default": None,
                },
                "where": where_clause,
            },
            "required": ["name", "columns"],
            "additionalProperties": False,
        },
    }
}

schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble tables configuration file schema",
    "type": "object",
    "properties": properties,
}
