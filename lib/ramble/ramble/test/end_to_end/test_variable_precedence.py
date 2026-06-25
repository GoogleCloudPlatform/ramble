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

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "mutable_mock_apps_repo",
    "mock_modifiers",
)

config = RambleCommand("config")
workspace = RambleCommand("workspace")


def test_variable_cross_pass_precedence(workspace_name):
    """Test that a specific when block overrides a generic one across evaluation passes."""
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        # Edit workspace config directly
        with open(ws.config_file_path, encoding="utf-8") as f:
            import yaml

            data = yaml.safe_load(f)

        data["ramble"]["modifiers"] = [{"name": "precedence-test", "mode": "test_mode"}]
        data["ramble"]["variants"] = {"trigger": "True"}

        with open(ws.config_file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        ws._re_read()

        workspace("setup", "--dry-run", global_args=global_args)

        exec_file = os.path.join(
            ws.experiment_dir,
            "when-variants",
            "test_wl",
            "generated",
            "execute_experiment",
        )

        with open(exec_file, encoding="utf-8") as f:
            exec_data = f.read()

        assert "echo 'specific'" in exec_data
