# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

metadata_schema_version = 0.1
metadata_schema = {
    0.1: {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
        },
        "required": ["key", "value", "timestamp"],
        "additionalProperties": False,
    }
}
