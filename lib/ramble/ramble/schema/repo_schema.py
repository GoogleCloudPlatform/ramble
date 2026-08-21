# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Helper utilities and schemas for repository configurations in Ramble.

.. literalinclude:: _ramble_root/lib/ramble/ramble/schema/repo_schema.py
   :lines: 13-
"""

from typing import Any, Dict, List, Optional


def make_repo_properties(section_name: str) -> Dict[str, Any]:
    """Generates the jsonschema properties dict for a repository configuration section."""
    return {
        section_name: {
            "type": "array",
            "default": [],
            "items": {"type": "string"},
        },
    }


def make_repo_schema(section_name: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Generates the full jsonschema dict for a repository configuration section."""
    if title is None:
        clean_name = section_name.replace("_repos", "").replace("_", " ")
        if clean_name == "repos":
            clean_name = ""
        else:
            clean_name = f" {clean_name}"
        title = f"Ramble{clean_name} repository configuration file schema"
    return {
        "$schema": "http://json-schema.org/schema#",
        "title": title,
        "type": "object",
        "additionalProperties": False,
        "properties": make_repo_properties(section_name),
    }


#: All repository configuration sections in Ramble
REPO_SECTIONS: List[str] = [
    "repos",
    "modifier_repos",
    "package_manager_repos",
    "workflow_manager_repos",
    "system_repos",
    "platform_repos",
    "base_class_repos",
    "base_application_repos",
    "base_modifier_repos",
    "base_package_manager_repos",
    "base_workflow_manager_repos",
    "base_system_repos",
    "base_platform_repos",
    "utility_repos",
    "base_utility_repos",
]

#: Dict containing properties for all repository sections
properties: Dict[str, Any] = {}
for section in REPO_SECTIONS:
    properties.update(make_repo_properties(section))

#: Dict mapping section name -> full schema for that repository section
schemas: Dict[str, Dict[str, Any]] = {
    section: make_repo_schema(section) for section in REPO_SECTIONS
}
