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
        "required": ["name", "value", "unit", "origin", "origin_type", "context", "experiment_id", "experiment_name"],
        "additionalProperties": False,
    }
}
