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


def test_workspace_dollar_paths(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]

    replacement_paths = ws.workspace_paths()

    path_args = []
    for name in replacement_paths:
        path_args.append("-v")
        path_args.append(f"test_{name}=${name}/unit_test")

    workspace(
        "manage", "experiments", "hostname", "--wf", "local", *path_args, global_args=global_args
    )

    with open(os.path.join(ws.config_dir, "execute_experiment.tpl"), "a") as f:
        for name in replacement_paths:
            f.write(f"{{test_{name}}}\n")

    ws._re_read()

    workspace(
        "setup",
        "--dry-run",
        global_args=global_args,
    )

    exec_path = os.path.join(
        ws.experiment_dir, "hostname", "local", "generated", "execute_experiment"
    )
    with open(exec_path) as f:
        data = f.read()
        for path in replacement_paths.values():
            assert path in data
