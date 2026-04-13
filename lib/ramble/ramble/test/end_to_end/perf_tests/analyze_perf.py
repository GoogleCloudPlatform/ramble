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
)

workspace = RambleCommand("workspace")


@pytest.mark.perf
@pytest.mark.maybeslow
def test_analyze_large_file(workspace_name, ramble_benchmark):
    global_args = ["-w", workspace_name]
    ws = ramble.workspace.create(workspace_name)
    workspace(
        "manage",
        "experiments",
        "sleep",
        "--wf",
        "rand_sleep",
        "-v",
        "n_nodes=1",
        "-v",
        "processes_per_node=1",
        "-v",
        "batch_submit={execute_experiment}",
        global_args=global_args,
    )
    ws._re_read()
    workspace("setup", "--dry-run", global_args=global_args)
    out_file = os.path.join(ws.experiment_dir, "sleep", "rand_sleep", "generated", "generated.out")
    with open(out_file, "w") as f:
        # Write 10 million lines to simulate a large output file
        for _ in range(10_000):
            f.write("no match\n" * 1_000)
        f.write("Sleep for 10 seconds\n")

    output = ramble_benchmark(workspace, "analyze", "-p", global_args=global_args)

    assert "Status = SUCCESS" in output
    assert "Sleep time = 10 s" in output
