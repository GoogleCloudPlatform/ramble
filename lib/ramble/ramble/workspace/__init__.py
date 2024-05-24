# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
"""This package implements Ramble workspaces.
"""

from .workspace import (
    Workspace,
    RambleWorkspaceError,
    RambleConflictingDefinitionError,
    RambleActiveWorkspaceError,
    RambleMissingApplicationError,
    RambleMissingWorkloadError,
    RambleMissingExperimentError,
    RambleMissingApplicationDirError,
    RambleInvalidTemplateNameError,
    activate,
    active,
    active_workspace,
    all_workspace_names,
    all_workspaces,
    config_dict,
    create,
    deactivate,
    default_config_yaml,
    exists,
    is_workspace_dir,
    get_workspace_path,
    config_file,
    config_file_name,
    workspace_software_path,
    auxiliary_software_dir_name,
    template_path,
    all_template_paths,
    no_active_workspace,
    read,
    root,
    ramble_workspace_var,
    namespace,
    workspace_config_path,
    workspace_log_path,
    workspace_shared_path
)

__all__ = [
    'Workspace',
    'RambleWorkspaceError',
    'RambleConflictingDefinitionError',
    'RambleActiveWorkspaceError',
    'RambleMissingApplicationError',
    'RambleMissingWorkloadError',
    'RambleMissingExperimentError',
    'RambleMissingApplicationDirError',
    'RambleInvalidTemplateNameError',
    'activate',
    'active',
    'active_workspace',
    'all_workspace_names',
    'all_workspaces',
    'config_dict',
    'create',
    'deactivate',
    'default_config_yaml',
    'exists',
    'is_workspace_dir',
    'get_workspace_path',
    'config_file',
    'config_file_name',
    'workspace_software_path',
    'auxiliary_software_dir_name',
    'template_path',
    'all_template_paths',
    'no_active_workspace',
    'read',
    'root',
    'ramble_workspace_var',
    'namespace',
    'workspace_config_path',
    'workspace_log_path',
    'workspace_shared_path',
]
