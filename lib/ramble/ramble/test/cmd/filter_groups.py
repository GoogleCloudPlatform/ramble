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
    with open(ws.config_file_path, encoding="utf-8") as f:
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
        "-v",
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
    assert ws.config_file_path in out
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
    with open(ws.config_file_path, encoding="utf-8") as f:
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
    with open(user_config_file, encoding="utf-8") as f:
        content = f.read()
        assert "filter_groups:" in content
        assert "global-small:" in content
        assert "{n_nodes} < 2" in content

    # 2. List global filter groups
    out = filter_groups_cmd("list", "-v")
    assert "global-small:" in out
    assert "{n_nodes} < 2" in out

    # 3. Add a group with --scope workspace (requires active workspace)
    ws = ramble.workspace.create(workspace_name)
    ramble.workspace.activate(ws)
    global_args = ["-w", workspace_name]

    try:
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
        with open(ws.config_file_path, encoding="utf-8") as f:
            ws_content = f.read()
            assert "ws-group:" in ws_content
            assert "{n_nodes} == 4" in ws_content

        with open(user_config_file, encoding="utf-8") as f:
            user_content = f.read()
            assert "ws-group:" not in user_content

        # 4. Blame from top-level command
        out = filter_groups_cmd("blame", global_args=global_args)
        assert ws.config_file_path in out
        assert "global-small" in out
        assert "ws-group" in out
    finally:
        ramble.workspace.deactivate()

    # 5. Remove global group
    filter_groups_cmd(
        "remove",
        "-n",
        "global-small",
    )

    with open(user_config_file, encoding="utf-8") as f:
        content = f.read()
        assert "global-small:" not in content


def test_workspace_manage_filter_groups_empty_list(workspace_name):
    ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]
    out = workspace_cmd("manage", "filter-groups", "list", global_args=global_args)
    assert "No filter groups defined" in out


def test_workspace_manage_filter_groups_errors(workspace_name):
    ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]

    workspace_cmd(
        "manage", "filter-groups", "add", "-n", "foo", global_args=global_args, fail_on_error=False
    )
    assert workspace_cmd.returncode != 0

    # Reserved keyword
    workspace_cmd(
        "manage",
        "filter-groups",
        "add",
        "-n",
        "and",
        "--where",
        "x",
        global_args=global_args,
        fail_on_error=False,
    )
    assert workspace_cmd.returncode != 0

    # Invalid characters
    workspace_cmd(
        "manage",
        "filter-groups",
        "add",
        "-n",
        "foo.bar",
        "--where",
        "x",
        global_args=global_args,
        fail_on_error=False,
    )
    assert workspace_cmd.returncode != 0

    workspace_cmd(
        "manage",
        "filter-groups",
        "remove",
        "-n",
        "foo",
        global_args=global_args,
        fail_on_error=False,
    )
    assert workspace_cmd.returncode != 0

    workspace_cmd(
        "manage", "filter-groups", "add", "-n", "foo", "--where", "x", global_args=global_args
    )
    workspace_cmd(
        "manage", "filter-groups", "add", "-n", "foo", "--where", "y", global_args=global_args
    )


def test_global_filter_groups_empty_list():
    out = filter_groups_cmd("list")
    assert "No filter groups defined" in out


def test_global_filter_groups_errors(workspace_name):
    filter_groups_cmd("add", "-n", "foo", fail_on_error=False)
    assert filter_groups_cmd.returncode != 0

    # Reserved keyword
    filter_groups_cmd("add", "-n", "and", "--where", "x", fail_on_error=False)
    assert filter_groups_cmd.returncode != 0

    # Invalid characters
    filter_groups_cmd("add", "-n", "foo.bar", "--where", "x", fail_on_error=False)
    assert filter_groups_cmd.returncode != 0

    filter_groups_cmd("remove", "-n", "foo", fail_on_error=False)
    assert filter_groups_cmd.returncode != 0

    filter_groups_cmd("add", "-n", "foo", "--where", "x")
    filter_groups_cmd("add", "-n", "foo", "--where", "y")

    filter_groups_cmd("add", "-n", "bar", "--exclude-where", "z")
    out = filter_groups_cmd("list", "-v")
    assert "exclude_where:" in out
    assert "z" in out

    out = filter_groups_cmd("blame")
    assert "exclude_where:" in out

    with pytest.raises(SystemExit):
        filter_groups_cmd("--scope", "workspace", "list", fail_on_error=False)

    ws = ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]
    ramble.workspace.activate(ws)
    try:
        filter_groups_cmd(
            "--scope", "workspace", "add", "-n", "ws-foo", "--where", "x", global_args=global_args
        )
        filter_groups_cmd(
            "--scope", "workspace", "remove", "-n", "ws-foo", global_args=global_args
        )
    finally:
        ramble.workspace.deactivate()


def test_global_filter_groups_no_subcommand(capsys):
    with pytest.raises(SystemExit):
        filter_groups_cmd()
    captured = capsys.readouterr()
    assert "the following arguments are required: ACTION" in captured.err


def test_workspace_manage_filter_groups_scopes(workspace_name):
    ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]

    # Add global (user scope) filter group using workspace manage filter-groups
    workspace_cmd(
        "manage",
        "filter-groups",
        "--scope",
        "user",
        "add",
        "-n",
        "user-fg",
        "--where",
        "y",
        global_args=global_args,
    )

    # Add workspace scope filter group
    workspace_cmd(
        "manage",
        "filter-groups",
        "--scope",
        "workspace",
        "add",
        "-n",
        "ws-fg",
        "--where",
        "x",
        global_args=global_args,
    )

    # List all scopes (no scope specified)
    out = workspace_cmd(
        "manage",
        "filter-groups",
        "list",
        global_args=global_args,
    )
    assert "user" in out
    assert "user-fg" in out
    assert "workspace" in out
    assert "ws-fg" in out

    # List only user scope
    out_user = workspace_cmd(
        "manage",
        "filter-groups",
        "--scope",
        "user",
        "list",
        global_args=global_args,
    )
    assert "user-fg" in out_user
    assert "ws-fg" not in out_user

    # Remove user scope filter group
    workspace_cmd(
        "manage",
        "filter-groups",
        "--scope",
        "user",
        "remove",
        "-n",
        "user-fg",
        global_args=global_args,
    )

    # Verify removed
    out_user_after = workspace_cmd(
        "manage",
        "filter-groups",
        "--scope",
        "user",
        "list",
        global_args=global_args,
    )
    assert "No filter groups defined in scope 'user'" in out_user_after


def test_filter_groups_precedence_overwrite(workspace_name):
    # 1. Create workspace
    ws = ramble.workspace.create(workspace_name)
    ramble.workspace.activate(ws)

    try:
        # 2. Add a filter group to user scope
        filter_groups_cmd(
            "--scope",
            "user",
            "add",
            "-n",
            "test-precedence",
            "--where",
            "{n_nodes} == 16",
        )

        # 3. Add same filter group to workspace scope
        filter_groups_cmd(
            "--scope",
            "workspace",
            "add",
            "-n",
            "test-precedence",
            "--where",
            "{n_nodes} == 42",
        )

        # 4. Get the merged filter groups
        fg = ramble.config.get("filter_groups")
        assert "test-precedence" in fg
        # The list in 'where' should only contain '{n_nodes} == 42',
        # NOT ['{n_nodes} == 42', '{n_nodes} == 16']
        assert fg["test-precedence"]["where"] == ["{n_nodes} == 42"]
    finally:
        ramble.workspace.deactivate()


def test_empty_filter_group_behavior(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    ramble.workspace.activate(ws)
    global_args = ["-w", workspace_name]

    try:
        # Set an empty filter group directly in the workspace config
        with ws.write_transaction():
            ramble.config.set("filter_groups:empty-fg", {}, scope=ws.ws_file_config_scope_name())

        # Verify that we can update it (add elements) and it logs "Updating existing filter group"
        out = workspace_cmd(
            "manage",
            "filter-groups",
            "add",
            "-n",
            "empty-fg",
            "--where",
            "{n_nodes} < 4",
            global_args=global_args,
        )
        assert "Updating existing filter group 'empty-fg'" in out

        # Reset it to empty
        with ws.write_transaction():
            ramble.config.set("filter_groups:empty-fg", {}, scope=ws.ws_file_config_scope_name())

        # Try removing it. It should succeed and print "Removing filter group"
        out = workspace_cmd(
            "manage",
            "filter-groups",
            "remove",
            "-n",
            "empty-fg",
            global_args=global_args,
        )
        assert "Removing filter group 'empty-fg'" in out
    finally:
        ramble.workspace.deactivate()
