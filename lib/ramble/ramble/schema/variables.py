# Copyright 2022-2024 Google LLC and other Ramble developers
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for variables configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/variables.py
   :lines: 12-
"""  # noqa E501

import ramble.schema.types


variables_def = {
    'type': ['object', 'null'],
    'default': {},
    'properties': {},
    'additionalProperties': ramble.schema.types.array_or_scalar_of_strings_or_nums
}

properties = {
    'variables': variables_def
}

#: Full schema with metadata
schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'Ramble variables configuration file schema',
    'type': 'object',
    'additionalProperties': False,
    'properties': properties
}
