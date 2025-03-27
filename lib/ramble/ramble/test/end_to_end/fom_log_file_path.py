# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.config
import ramble.software_environments
import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config", "mutable_mock_workspace_path", "mock_applications"
)

on = RambleCommand("on")
workspace = RambleCommand("workspace")


def test_relative_fom_log_works(mutable_config, mutable_mock_workspace_path, request):
    workspace_name = request.node.name

    global_args = ["-w", workspace_name]

    ws = ramble.workspace.create(workspace_name)
    workspace(
        "manage",
        "experiments",
        "fom-log-path",
        "-v",
        "n_nodes=1",
        "-v",
        "n_ranks=1",
        "-v",
        "batch_submit={execute_experiment}",
        global_args=global_args,
    )
    ws._re_read()

    workspace("setup", global_args=global_args)

    on(global_args=global_args)

    workspace("analyze", global_args=global_args)

    with open(os.path.join(ws.root, "results.latest.txt")) as f:
        data = f.read()

        assert "FAILED" not in data
        assert "SUCCESS" in data
        assert "test_fom = test" in data
