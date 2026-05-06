# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

fom_schema_version = 0.1
fom_schema = {
    0.1: {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "value": {"type": "string"},
            "unit": {"type": "string"},
            "origin": {"type": "string"},
            "origin_type": {"type": "string"},
            "context": {"type": "string"},
            "experiment_id": {"type": "integer"},
            "experiment_name": {"type": "string"},
        },
        "required": [
            "name",
            "value",
            "unit",
            "origin",
            "origin_type",
            "context",
            "experiment_id",
            "experiment_name",
        ],
        "additionalProperties": False,
    }
}
