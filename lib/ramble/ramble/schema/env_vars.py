# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for environment variables configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/env_vars.py
   :lines: 12-
"""  # noqa E501

import ramble.schema.licenses


#: Properties for inclusion in other schemas
properties = {
    "env_vars": ramble.schema.licenses.env_var_actions,
}

#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble environment variable configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}
