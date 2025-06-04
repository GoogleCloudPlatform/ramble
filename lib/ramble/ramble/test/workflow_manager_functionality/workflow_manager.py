# Copyright 2022-2025 The Ramble Authors
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


def test_default_workflow_manager_banner(workspace_name):
    test_config = """
ramble:
  variables:
    processes_per_node: 1
    n_nodes: 1
    mpi_command: ""
    batch_submit: ""
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test_default: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()
        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)
        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()
        workspace("setup", "--dry-run", global_args=["-D", ws.root])

        path = os.path.join(ws.experiment_dir, "hostname", "local", "test_default")
        with open(os.path.join(path, "execute_experiment")) as f:
            content = f.read()
            assert "{workflow_banner}" not in content
            assert (
                "If this file is not the same as the above path, it is unlikely that this script"
                in content
            )
