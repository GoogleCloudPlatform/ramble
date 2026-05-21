# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
from ramble.error import ConflictingModifiersError
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")


def define_experiments(global_args):
    workspace(
        "manage",
        "experiments",
        "hostname",
        "--wf",
        "local",
        "-v",
        "n_nodes=1",
        "-v",
        "n_ranks=1",
        "--default-variable-value",
        "1",
        global_args=global_args,
    )


def test_name_modifier_conflict(mutable_mock_workspace_path, mock_modifiers, workspace_name):
    global_args = ["-w", workspace_name]
    ramble.workspace.create(workspace_name)

    define_experiments(global_args)

    for _ in range(2):
        workspace(
            "manage",
            "modifiers",
            "--add",
            "--name",
            "conflict-name-modifier",
            "--scope",
            "workspace",
            global_args=global_args,
        )

    with pytest.raises(ConflictingModifiersError) as err:
        workspace("setup", global_args=global_args)
        assert "by having the same name." in str(err)


def test_name_mode_modifier_conflict(mutable_mock_workspace_path, mock_modifiers, workspace_name):
    global_args = ["-w", workspace_name]
    ramble.workspace.create(workspace_name)

    define_experiments(global_args)

    for _ in range(2):
        workspace(
            "manage",
            "modifiers",
            "--add",
            "--name",
            "conflict-name-mode-modifier",
            "--scope",
            "workspace",
            global_args=global_args,
        )

    with pytest.raises(ConflictingModifiersError) as err:
        workspace("setup", global_args=global_args)
        assert "by having the same name and mode." in err


def test_name_executables_modifier_conflict(
    mutable_mock_workspace_path, mock_modifiers, workspace_name
):
    global_args = ["-w", workspace_name]
    ramble.workspace.create(workspace_name)

    define_experiments(global_args)

    for _ in range(2):
        workspace(
            "manage",
            "modifiers",
            "--add",
            "--name",
            "conflict-name-executables-modifier",
            "--scope",
            "workspace",
            "-e",
            "foo",
            global_args=global_args,
        )

    with pytest.raises(ConflictingModifiersError) as err:
        workspace("setup", global_args=global_args)
        assert "by having the same name and overlapping on_executable." in err


def test_name_mode_executables_modifier_conflict(
    mutable_mock_workspace_path, mock_modifiers, workspace_name
):
    global_args = ["-w", workspace_name]
    ramble.workspace.create(workspace_name)

    define_experiments(global_args)

    for _ in range(2):
        workspace(
            "manage",
            "modifiers",
            "--add",
            "--name",
            "conflict-name-mode-executables-modifier",
            "--scope",
            "workspace",
            "-e",
            "foo",
            global_args=global_args,
        )

    with pytest.raises(ConflictingModifiersError) as err:
        workspace("setup", global_args=global_args)
        assert "by having the same name, mode, and overlapping on_executable." in err
