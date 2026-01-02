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

workspace = RambleCommand("workspace")

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)


@pytest.mark.maybeslow
def test_workflow_manager_foms(mutable_mock_wms_repo, workspace_name):
    test_config = """
ramble:
  variants:
    workflow_manager: wm-with-foms
  variables:
    mpi_command: ""
    batch_submit: "{execute_experiment}"
    processes_per_node: 1
    n_nodes: 1
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()
        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)
        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()
        workspace("setup", "--dry-run", global_args=["-D", ws.root])

        workspace("analyze", "-p", global_args=["-D", ws.root])
        result_file = os.path.join(ws.root, "results.latest.txt")
        with open(result_file) as f:
            assert "job-status = RUNNING" in f.read()
