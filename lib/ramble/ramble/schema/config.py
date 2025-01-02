# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Schema for config.yaml configuration file.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/config.py
   :lines: 15-
"""

import spack.schema.config

#: Properties for inclusion in other schemas
properties = {
    "config": {**spack.schema.config.properties["config"]},
}

properties["config"]["shell"] = {"type": "string", "enum": ["sh", "bash", "csh", "tcsh", "fish"]}

properties["config"]["spack"] = {
    "type": "object",
    "default": {"install": {"flags": "--reuse"}, "concretize": {"flags": "--reuse"}},
    "properties": {
        "global": {
            "type": "object",
            "default": {"flags": ""},
            "properties": {"flags": {"type": "string", "default": ""}},
            "additionalProperties": False,
        },
        "install": {
            "type": "object",
            "default": {
                "flags": "--reuse",
                "prefix": "",
            },
            "properties": {
                "flags": {
                    "type": "string",
                    "default": "--reuse",
                },
                "prefix": {"type": "string", "default": ""},
            },
            "additionalProperties": False,
        },
        "concretize": {
            "type": "object",
            "default": {
                "flags": "--reuse",
                "prefix": "",
            },
            "properties": {
                "flags": {
                    "type": "string",
                    "default": "--reuse",
                },
                "prefix": {"type": "string", "default": ""},
            },
            "additionalProperties": False,
        },
        "compiler_find": {
            "type": "object",
            "default": {
                "flags": "",
                "prefix": "",
            },
            "properties": {
                "flags": {
                    "type": "string",
                    "default": "",
                },
                "prefix": {"type": "string", "default": ""},
            },
        },
        "buildcache": {
            "type": "object",
            "default": {
                "flags": "",
                "prefix": "",
            },
            "properties": {
                "flags": {
                    "type": "string",
                    "default": "",
                },
                "prefix": {"type": "string", "default": ""},
            },
            "additionalProperties": False,
        },
        "env_create": {
            "type": "object",
            "default": {
                "flags": "",
            },
            "properties": {
                "flags": {
                    "type": "string",
                    "default": "",
                },
            },
            "additionalProperties": False,
        },
        "env_view": {
            "type": "object",
            "default": {
                "link_type": "symlink",
            },
            "properties": {
                "link_type": {
                    "type": "string",
                    "default": "symlink",
                },
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

properties["config"]["spack"]["flags"] = {}

properties["config"]["pip"] = {
    "type": "object",
    "default": {"install": {"flags": []}},
    "properties": {
        "install": {
            "type": "object",
            "properties": {
                "flags": {
                    "type": "array",
                    "default": [],
                    "items": {
                        "type": "string",
                    },
                },
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

properties["config"]["input_cache"] = {"type": "string", "default": "$ramble/var/ramble/cache"}

properties["config"]["workspace_dirs"] = {
    "type": "string",
    "default": "$ramble/var/ramble/workspaces",
}

properties["config"]["report_dirs"] = {
    "type": "string",
    "default": "~/.ramble/reports",
}

properties["config"]["upload"] = {
    "type": "object",
    "properties": {
        "uri": {"type": "string", "default": ""},
        "push_failed": {"type": "boolean", "default": True},
        "type": {"type": "string", "default": "BigQuery", "enum": ["BigQuery", "PrintOnly"]},
    },
}

properties["config"]["user"] = {"type": "string", "default": ""}

properties["config"]["disable_passthrough"] = {"type": "boolean", "default": False}

properties["config"]["disable_progress_bar"] = {"type": "boolean", "default": False}

properties["config"]["disable_logger"] = {"type": "boolean", "default": False}

properties["config"]["n_repeats"] = {"type": "string", "default": "0"}

properties["config"]["repeat_success_strict"] = {"type": "boolean", "default": True}


#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble core configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}


def update(data):
    """Update the data in place to remove deprecated properties.

    Args:
        data (dict): dictionary to be updated

    Returns:
        True if data was changed, False otherwise
    """
    changed = False

    # There are no currently deprecated properties.
    # This is a stub to allow deprecated properties to be removed later, once
    # they exist.

    # Convert `spack_flags` to `spack:command_flags`

    spack_flags = data.get("spack_flags", None)
    if isinstance(spack_flags, dict):
        if data.get("spack", None) is None:
            data["spack"] = {"flags": {}}

        global_args = spack_flags.get("global_args", None)
        if global_args is not None:
            data["spack"]["global"] = {"flags": global_args}

        install_flags = spack_flags.get("install", None)
        if install_flags is not None:
            data["spack"]["install"] = {"flags": install_flags}

        concretize_flags = spack_flags.get("concretize", None)
        if concretize_flags is not None:
            data["spack"]["concretize"] = {"flags": concretize_flags}

        del data["spack_flags"]
        changed = True

    return changed
