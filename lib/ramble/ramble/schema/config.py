# Copyright 2022-2026 The Ramble Authors
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

import copy
from typing import Any, Dict

import spack.schema.config

#: Properties for inclusion in other schemas
properties: Dict[str, Any] = {
    "config": copy.deepcopy(spack.schema.config.properties["config"]),
}

config_props = properties["config"]["properties"]

config_props["shell"] = {
    "type": "string",
    "enum": ["sh", "bash", "csh", "tcsh", "fish"],
    "default": "bash",
}

config_props["spack"] = {
    "type": "object",
    "default": {"install": {"flags": "--fresh"}, "concretize": {"flags": "--fresh"}},
    "properties": {
        "flags": {
            "type": "object",
            "default": {},
        },
        "global": {
            "type": "object",
            "default": {"flags": ""},
            "properties": {"flags": {"type": "string", "default": ""}},
            "additionalProperties": False,
        },
        "install": {
            "type": "object",
            "default": {
                "flags": "--fresh",
                "prefix": "",
            },
            "properties": {
                "flags": {
                    "type": "string",
                    "default": "--fresh",
                },
                "prefix": {"type": "string", "default": ""},
            },
            "additionalProperties": False,
        },
        "concretize": {
            "type": "object",
            "default": {
                "flags": "--fresh",
                "prefix": "",
            },
            "properties": {
                "flags": {
                    "type": "string",
                    "default": "--fresh",
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

config_props["pip"] = {
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

config_props["input_cache"] = {"type": "string", "default": "$ramble/var/ramble/cache"}

config_props["workspace_dirs"] = {
    "type": ["string", "array"],
    "items": {"type": "string"},
    "default": "$ramble/var/ramble/workspaces",
}

config_props["report_dirs"] = {
    "type": "string",
    "default": "~/.ramble/reports",
}

config_props["upload"] = {
    "type": "object",
    "properties": {
        "uri": {"type": "string", "default": ""},
        "push_failed": {"type": "boolean", "default": True},
        "type": {
            "type": "string",
            "enum": ["BigQuery", "PrintOnly", "SQLite"],
            "default": "BigQuery",
        },
    },
    "additionalProperties": False,
}

config_props["user"] = {"type": "string", "default": ""}

config_props["disable_passthrough"] = {"type": "boolean", "default": False}

config_props["disable_progress_bar"] = {"type": "boolean", "default": False}

config_props["disable_logger"] = {"type": "boolean", "default": False}

config_props["aggregate_warnings"] = {"type": "boolean", "default": False}

config_props["suppress_warnings"] = {"type": "boolean", "default": False}

config_props["n_repeats"] = {"type": ["string", "integer"], "default": "0"}

config_props["repeat_success_strict"] = {"type": "boolean", "default": True}

config_props["enable_workspace_prompt"] = {"type": "boolean", "default": False}

config_props["enable_strict_versions"] = {"type": "boolean", "default": True}

config_props["overwrite_inventories"] = {"type": "boolean", "default": False}

config_props["generate_file_editing_scripts"] = {"type": "boolean", "default": True}

config_props["bootstrap_utilities"] = {"type": "boolean", "default": True}

config_props["include_phase_dependencies"] = {"type": "boolean", "default": False}

config_props["include_workspace_comments"] = {"type": "boolean", "default": True}

config_props["resolve_variables_in_subprocesses"] = {"type": "boolean", "default": False}

config_props["archive_url"] = {"type": "string", "default": ""}

config_props["aliases"] = {
    "type": "object",
    "default": {},
    "additionalProperties": {"type": "string"},
}

config_props["stage_method"] = {
    "type": "string",
    "enum": ["cp", "rsync", "symbolic_link", "hard_link"],
    "default": "cp",
}


#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Ramble core configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}


def update(data: Dict[str, Any]) -> bool:
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

    spack_flags = data.get("spack_flags")
    if isinstance(spack_flags, dict):
        if data.get("spack") is None:
            data["spack"] = {"flags": {}}

        global_args = spack_flags.get("global_args")
        if global_args is not None:
            data["spack"]["global"] = {"flags": global_args}

        install_flags = spack_flags.get("install")
        if install_flags is not None:
            data["spack"]["install"] = {"flags": install_flags}

        concretize_flags = spack_flags.get("concretize")
        if concretize_flags is not None:
            data["spack"]["concretize"] = {"flags": concretize_flags}

        del data["spack_flags"]
        changed = True

    return changed
