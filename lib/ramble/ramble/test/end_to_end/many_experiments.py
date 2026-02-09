# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


@pytest.mark.maybeslow
def test_many_experiments(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    ws.write()
    global_args = ["-w", workspace_name]

    workspace(
        "manage",
        "experiments",
        "hostname",
        "--wf",
        "local",
        "-e",
        "test-{n_nodes}-{var1}-{var2}-{var3}",
        "-v",
        "n_ranks='{n_nodes}*{processes_per_node}'",
        "-v",
        "n_nodes=[1,2,4,8,16,32,64,128,256]",
        "-v",
        "var1=[1,2,3,4,5,6,7,8,9,10]",
        "-v",
        "var2=[1,2,3,4,5,6,7,8,9,10]",
        "-v",
        "var3=[1,2,3,4,5,6,7,8,9,10]",
        "-m",
        "n_nodes,var1,var2,var3",
        global_args=global_args,
    )

    output = workspace("info", global_args=global_args)

    assert "Experiment 8100" in output
