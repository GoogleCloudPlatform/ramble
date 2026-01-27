# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.error
import ramble.workspace
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "mutable_mock_apps_repo",
    "mutable_mock_mods_repo",
    "mutable_mock_pkg_mans_repo",
    "mutable_mock_wms_repo",
)

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "test_args,disabled_value,enabled_value",
    [
        (
            ["--wm", "when-workflow-manager"],
            "object_precedence_var from application",
            "object_precedence_var from workflow_manager",
        ),
    ],
)
def test_object_precedence_variables(workspace_name, test_args, disabled_value, enabled_value):
    global_args = ["-w", workspace_name]

    ws = ramble.workspace.create(workspace_name)
    workspace(
        "manage",
        "experiments",
        "basic",
        "-v",
        "n_nodes=3",
        "-v",
        "processes_per_node=1",
        "-v",
        "batch_submit={execute_experiment}",
        "--wf",
        "test_wl",
        *test_args,
        global_args=global_args,
    )

    with open(os.path.join(ws.config_dir, "test.tpl"), "w+") as f:
        f.write("{object_precedence_var}")

    variants_file = os.path.join(ws.config_dir, "variants.yaml")
    test_file = os.path.join(ws.experiment_dir, "basic", "test_wl", "generated", "test")

    workspace("setup", "--dry-run", global_args=global_args)

    with open(test_file) as f:
        assert disabled_value in f.read()

    with open(variants_file, "w+") as f:
        f.write(
            """variants:
  set_precedence_var: True"""
        )

    workspace("setup", "--dry-run", global_args=global_args)

    with open(test_file) as f:
        assert enabled_value in f.read()
