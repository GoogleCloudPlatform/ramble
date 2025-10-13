# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import argparse
import os
import shutil

import pytest

from ramble.workspace import workspace

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_mock_workspace_path",
    "config",
    "mutable_mock_apps_repo",
    "workspace_deactivate",
)


def test_re_read(tmpdir):
    with tmpdir.as_cwd():
        test_workspace = workspace.Workspace(os.getcwd(), True)
        test_workspace.clear()
        test_workspace._re_read()


def test_read_file_content(tmpdir):
    with tmpdir.as_cwd():
        test_workspace = workspace.Workspace(os.getcwd(), True)
        fname = "test.tpl"
        with open(fname, "w+") as f:
            f.write("test content read")
        assert test_workspace.read_file_content(fname) == "test content read"
        with open(fname, "w") as f:
            f.write("test content read modified")
        # The read is cached and does not reflect the latest content
        assert test_workspace.read_file_content(fname) == "test content read"


def test_all_workspaces():
    # Acknowledge that other workspaces may exist from other tests.
    initial_workspace_names = {ws.name for ws in workspace.all_workspaces()}

    # Create a valid workspace
    ws1_name = "test-ws-1"
    ws1 = workspace.create(ws1_name)
    ws1.write()

    # Create another valid workspace
    ws2_name = "test-ws-2"
    ws2 = workspace.create(ws2_name)
    ws2.write()

    # Create a directory that is not a workspace (no config)
    not_a_ws_path = workspace.root("not-a-workspace")
    os.makedirs(not_a_ws_path)

    # Create a directory with an invalid name
    invalid_path = os.path.join(workspace.get_workspace_path(), ".invalid-name")
    os.makedirs(invalid_path)

    # Create a file in the workspaces directory
    a_file_path = os.path.join(workspace.get_workspace_path(), "a-file")
    with open(a_file_path, "w") as f:
        f.write("I am a file, not a workspace.")

    try:
        current_workspace_names = {ws.name for ws in workspace.all_workspaces()}
        new_workspaces = current_workspace_names - initial_workspace_names

        assert new_workspaces == {ws1_name, ws2_name}

        # Check that they are indeed Workspace objects
        for ws in workspace.all_workspaces():
            if ws.name in new_workspaces:
                assert isinstance(ws, workspace.Workspace)
    finally:
        # Clean up our additions
        shutil.rmtree(workspace.root(ws1_name))
        shutil.rmtree(workspace.root(ws2_name))
        shutil.rmtree(not_a_ws_path)
        shutil.rmtree(invalid_path)
        os.remove(a_file_path)


def test_all_config_files():
    ws_name = "test-ws-config-files"
    ws_root = workspace.root(ws_name)
    try:
        ws = workspace.create(ws_name)
        ws.write()

        config_dir = os.path.join(ws_root, workspace.workspace_config_path)

        # Create another yaml file
        extra_yaml_path = os.path.join(config_dir, "extra.yaml")
        with open(extra_yaml_path, "w") as f:
            f.write("key: value")

        # Create a non-yaml file
        not_yaml_path = os.path.join(config_dir, "not.txt")
        with open(not_yaml_path, "w") as f:
            f.write("hello")

        config_files = workspace.all_config_files(ws_root)

        ramble_yaml_path = os.path.join(config_dir, workspace.config_file_name)

        assert len(config_files) == 2
        assert ramble_yaml_path in config_files
        assert extra_yaml_path in config_files

    finally:
        if os.path.exists(ws_root):
            shutil.rmtree(ws_root)


def test_template_path():
    ws_name = "test-ws-template-path"
    ws_root = workspace.root(ws_name)

    template_name = "my-template"

    path = workspace.template_path(ws_root, template_name)

    expected_path = os.path.join(
        ws_root,
        workspace.workspace_config_path,
        template_name + workspace.workspace_template_extension,
    )

    assert path == expected_path


def test_get_workspace():
    ws_name = "test-ws-get-ws"
    ws_root = workspace.root(ws_name)
    ws = None

    try:
        # Setup a workspace
        ws = workspace.create(ws_name)
        ws.write()

        # Scenario 1: by name
        args = argparse.Namespace(workspace=ws_name)
        ret_ws = workspace.get_workspace(args, "test-cmd")
        assert ret_ws.name == ws_name

        # Scenario 2: by path
        args = argparse.Namespace(workspace=ws_root)
        ret_ws = workspace.get_workspace(args, "test-cmd")
        assert ret_ws.root == ws_root

        # Scenario 3: active workspace
        workspace.activate(ws)
        args = argparse.Namespace()  # no workspace attribute
        ret_ws = workspace.get_workspace(args, "test-cmd")
        assert ret_ws.name == ws_name

        # Scenario 4: no workspace, required=True
        # Deactivate first to test this case
        workspace.deactivate()
        with pytest.raises(SystemExit):
            workspace.get_workspace(args, "test-cmd", required=True)
        # Reactivate for cleanup
        workspace.activate(ws)

        # Scenario 5: invalid workspace in args
        args = argparse.Namespace(workspace="non-existent-ws")
        with pytest.raises(workspace.RambleWorkspaceError):
            workspace.get_workspace(args, "test-cmd")

    finally:
        if ws:
            workspace.deactivate()
        if os.path.exists(ws_root):
            shutil.rmtree(ws_root)
