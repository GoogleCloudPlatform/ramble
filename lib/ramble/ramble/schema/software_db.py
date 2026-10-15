# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

software_db_schema_version = 0.1
software_db_schema = {
    0.1: {
        "type": "object",
        "properties": {
            "experiment_id": {"type": "integer"},
            "experiment_name": {"type": "string"},
            "name": {"type": "string"},
            "version": {"type": "string"},
            "compiler": {"type": "string"},
            "compiler_version": {"type": "string"},
            "target": {"type": "string"},
            "variants": {"type": "string"},
        },
        "required": [
            "experiment_id",
            "experiment_name",
            "name",
        ],
        "additionalProperties": False,
    }
}
