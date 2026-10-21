# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from enum import Enum
from typing import Any, Dict

ObjectTypes = Enum(
    "ObjectTypes",
    [
        "applications",
        "modifiers",
        "package_managers",
        "workflow_managers",
        "systems",
        "platforms",
        "base_classes",
        "base_applications",
        "base_modifiers",
        "base_package_managers",
        "base_workflow_managers",
        "base_systems",
        "base_platforms",
        "utilities",
        "base_utilities",
    ],
)

OBJECT_NAMES = [obj.name for obj in ObjectTypes]

default_type = ObjectTypes.applications

unified_config = "repo.yaml"

type_definitions: Dict[ObjectTypes, Dict[str, Any]] = {
    ObjectTypes.applications: {
        "file_name": "application.py",
        "dir_name": "applications",
        "abbrev": "app",
        "kit_name": "appkit",
        "template": "application.py.tpl",
        "default_base": "ExecutableApplication",
        "config_section": "repos",
        "accepted_configs": ["application_repo.yaml", unified_config],
        "singular": "application",
    },
    ObjectTypes.modifiers: {
        "file_name": "modifier.py",
        "dir_name": "modifiers",
        "abbrev": "mod",
        "kit_name": "modkit",
        "template": "modifier.py.tpl",
        "default_base": "BasicModifier",
        "config_section": "modifier_repos",
        "accepted_configs": ["modifier_repo.yaml", unified_config],
        "singular": "modifier",
    },
    ObjectTypes.package_managers: {
        "file_name": "package_manager.py",
        "dir_name": "package_managers",
        "abbrev": "pkg_man",
        "kit_name": "pkgmankit",
        "template": "package_manager.py.tpl",
        "default_base": "PackageManagerBase",
        "config_section": "package_manager_repos",
        "accepted_configs": ["package_manager_repo.yaml", unified_config],
        "singular": "package manager",
        "aliases": ["pkg", "package"],
    },
    ObjectTypes.workflow_managers: {
        "file_name": "workflow_manager.py",
        "dir_name": "workflow_managers",
        "abbrev": "wm",
        "kit_name": "wmkit",
        "template": "workflow_manager.py.tpl",
        "default_base": "WorkflowManagerBase",
        "config_section": "workflow_manager_repos",
        "accepted_configs": ["workflow_manager_repo.yaml", unified_config],
        "singular": "workflow manager",
        "aliases": ["workflow"],
    },
    ObjectTypes.systems: {
        "file_name": "system.py",
        "dir_name": "systems",
        "abbrev": "sys",
        "kit_name": "syskit",
        "default_base": "SystemBase",
        "config_section": "system_repos",
        "accepted_configs": ["system_repo.yaml", unified_config],
        "singular": "system",
    },
    ObjectTypes.platforms: {
        "file_name": "platform.py",
        "dir_name": "platforms",
        "abbrev": "plat",
        "kit_name": "platkit",
        "default_base": "PlatformBase",
        "config_section": "platform_repos",
        "accepted_configs": ["platform_repo.yaml", unified_config],
        "singular": "platform",
    },
    ObjectTypes.utilities: {
        "file_name": "utility.py",
        "dir_name": "utilities",
        "abbrev": "utility",
        "kit_name": "toolkit",
        "default_base": "UtilityBase",
        "config_section": "utility_repos",
        "accepted_configs": ["utility_repo.yaml", unified_config],
        "singular": "utility",
    },
    ObjectTypes.base_classes: {
        "file_name": "base_class.py",
        "dir_name": "base_classes",
        "abbrev": "base_cls",
        "kit_name": None,
        "config_section": "base_class_repos",
        "accepted_configs": ["base_class_repo.yaml", unified_config],
        "singular": "base class",
        "aliases": ["base"],
    },
}

for _obj_type, _tdef in list(type_definitions.items()):
    if _obj_type == ObjectTypes.base_classes:
        continue
    _base_type = ObjectTypes[f"base_{_obj_type.name}"]
    _stem = _tdef["singular"].replace(" ", "_")
    type_definitions[_base_type] = {
        **_tdef,
        "file_name": f"base_{_tdef['file_name']}",
        "dir_name": f"base_{_tdef['dir_name']}",
        "abbrev": f"base_{_tdef['abbrev']}",
        "config_section": f"base_{_stem}_repos",
        "accepted_configs": [f"base_{_tdef['accepted_configs'][0]}", unified_config],
        "singular": f"base {_tdef['singular']}",
        **({"aliases": [f"base_{a}" for a in _tdef["aliases"]]} if "aliases" in _tdef else {}),
    }
