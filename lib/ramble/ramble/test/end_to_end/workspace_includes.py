# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


def test_workspace_add_includes(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]

    ws.write()

    output = workspace("manage", "includes", "--list", global_args=global_args)

    assert "Workspace contains no includes." in output

    workspace(
        "manage",
        "includes",
        "--add",
        "$workspace_configs/auxiliary_software_files",
        global_args=global_args,
    )

    ws._re_read()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path) as f:
        data = f.read()
        assert "- $workspace_configs/auxiliary_software_files" in data


def test_workspace_remove_includes_index(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]

    ws.write()

    output = workspace("manage", "includes", "--list", global_args=global_args)

    assert "Workspace contains no includes." in output

    workspace(
        "manage",
        "includes",
        "--add",
        "$workspace_configs/auxiliary_software_files",
        global_args=global_args,
    )

    ws._re_read()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    output = workspace("manage", "includes", "--list", global_args=global_args)

    assert "0: $workspace_configs/auxiliary_software_files" in output

    with open(config_path) as f:
        data = f.read()
        assert "- $workspace_configs/auxiliary_software_files" in data

    workspace("manage", "includes", "--remove-index", "0", global_args=global_args)

    ws._re_read()

    output = workspace("manage", "includes", "--list", global_args=global_args)

    assert "Workspace contains no includes." in output

    with open(config_path) as f:
        data = f.read()
        assert "- $workspace_configs/auxiliary_software_files" not in data


def test_workspace_remove_includes_pattern(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]

    ws.write()

    output = workspace("manage", "includes", "--list", global_args=global_args)

    assert "Workspace contains no includes." in output

    workspace(
        "manage",
        "includes",
        "--add",
        "$workspace_configs/auxiliary_software_files",
        global_args=global_args,
    )

    ws._re_read()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    output = workspace("manage", "includes", "--list", global_args=global_args)

    assert "0: $workspace_configs/auxiliary_software_files" in output

    with open(config_path) as f:
        data = f.read()
        assert "- $workspace_configs/auxiliary_software_files" in data

    workspace("manage", "includes", "--remove", "*aux*", global_args=global_args)

    ws._re_read()

    output = workspace("manage", "includes", "--list", global_args=global_args)

    assert "Workspace contains no includes." in output

    with open(config_path) as f:
        data = f.read()
        assert "- $workspace_configs/auxiliary_software_files" not in data
