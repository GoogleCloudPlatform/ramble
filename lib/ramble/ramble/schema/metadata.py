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
