# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.config
import ramble.workspace
from ramble.main import RambleCommand

# Use mutable_config to isolate global configs and mutable_mock_workspace_path for workspaces
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace_cmd = RambleCommand("workspace")
filter_groups_cmd = RambleCommand("filter-groups")


def test_workspace_manage_filter_groups(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]

    # 1. Add a filter group in workspace
    workspace_cmd(
        "manage",
        "filter-groups",
        "add",
        "-n",
        "small-scale",
        "--where",
        "{n_nodes} < 4",
        "--exclude-where",
        "{mpi} == 'tcp'",
        global_args=global_args,
    )

    # Verify it was added to workspace config file
    with open(ws.config_file_path) as f:
        content = f.read()
        assert "filter_groups:" in content
        assert "small-scale:" in content
        assert "where:" in content
        assert "{n_nodes} < 4" in content
        assert "exclude_where:" in content
        assert "{mpi}" in content
        assert "tcp" in content

    # 2. List filter groups in workspace
    out = workspace_cmd(
        "manage",
        "filter-groups",
        "list",
        global_args=global_args,
    )
    assert "small-scale:" in out
    assert "{n_nodes} < 4" in out
    assert "{mpi}" in out
    assert "tcp" in out

    # 3. Add another group in workspace
    workspace_cmd(
        "manage",
        "filter-groups",
        "add",
        "-n",
        "large-scale",
        "--where",
        "{n_nodes} >= 8",
        global_args=global_args,
    )

    # 4. Blame filter groups (should show workspace scope)
    out = workspace_cmd(
        "manage",
        "filter-groups",
        "blame",
        global_args=global_args,
    )
    assert "Scope: workspace:" in out
    assert "small-scale:" in out
    assert "large-scale:" in out

    # 5. Remove a group from workspace
    workspace_cmd(
        "manage",
        "filter-groups",
        "remove",
        "-n",
        "small-scale",
        global_args=global_args,
    )

    # Verify it was removed from file
    with open(ws.config_file_path) as f:
        content = f.read()
        assert "small-scale:" not in content
        assert "large-scale:" in content


def test_global_filter_groups(workspace_name):
    # 1. Add a global filter group (defaults to 'user' scope)
    filter_groups_cmd(
        "add",
        "-n",
        "global-small",
        "--where",
        "{n_nodes} < 2",
    )

    # Verify it was added to user config file
    user_scope = ramble.config.config.scopes["user"]
    user_config_file = user_scope.get_section_filename("filter_groups")

    assert os.path.exists(user_config_file)
    with open(user_config_file) as f:
        content = f.read()
        assert "filter_groups:" in content
        assert "global-small:" in content
        assert "{n_nodes} < 2" in content

    # 2. List global filter groups
    out = filter_groups_cmd("list")
    assert "global-small:" in out
    assert "{n_nodes} < 2" in out

    # 3. Add a group with --scope workspace (requires active workspace)
    ws = ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]

    filter_groups_cmd(
        "--scope",
        "workspace",
        "add",
        "-n",
        "ws-group",
        "--where",
        "{n_nodes} == 4",
        global_args=global_args,
    )

    # Verify it went to workspace config, not user config
    with open(ws.config_file_path) as f:
        ws_content = f.read()
        assert "ws-group:" in ws_content
        assert "{n_nodes} == 4" in ws_content

    with open(user_config_file) as f:
        user_content = f.read()
        assert "ws-group:" not in user_content

    # 4. Blame from top-level command
    out = filter_groups_cmd("blame", global_args=global_args)
    assert "Scope: user" in out
    assert "global-small:" in out
    assert "Scope: workspace:" in out
    assert "ws-group:" in out

    # 5. Remove global group
    filter_groups_cmd(
        "remove",
        "-n",
        "global-small",
    )

    with open(user_config_file) as f:
        content = f.read()
        assert "global-small:" not in content
