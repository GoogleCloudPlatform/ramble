# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

experiment_schema_version = 0.1
experiment_schema = {
    0.1: {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "id": {"type": "integer"},
            "data": {"type": "string"},
            "application_name": {"type": "string"},
            "workspace_name": {"type": "string"},
            "workspace_hash": {"type": "string"},
            "workload_name": {"type": "string"},
            "bulk_hash": {"type": "string"},
            "n_nodes": {"type": "integer"},
            "processes_per_node": {"type": "integer"},
            "n_ranks": {"type": "integer"},
            "n_threads": {"type": "integer"},
            "node_type": {"type": "string"},
            "status": {"type": "string"},
            "user": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
        },
        "required": [
            "name",
            "id",
            "data",
            "application_name",
            "workspace_name",
            "workspace_hash",
            "workload_name",
            "bulk_hash",
            "n_nodes",
            "processes_per_node",
            "n_ranks",
            "n_threads",
            "node_type",
            "status",
            "user",
            "timestamp",
        ],
        "additionalProperties": False,
    }
}
