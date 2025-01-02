# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.application
import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_workspace_setup_creates_inventory(
    mutable_config, mutable_mock_workspace_path, mock_applications
):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
              env_vars:
                set:
                  MY_VAR: 'TEST'
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_workspace_setup_creates_inventory"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()
        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        assert os.path.exists(
            os.path.join(ws.root, ramble.workspace.Workspace.inventory_file_name)
        )
        assert os.path.exists(os.path.join(ws.root, ramble.workspace.Workspace.hash_file_name))
        assert os.path.exists(
            os.path.join(
                ws.experiment_dir,
                "basic",
                "test_wl",
                "simple_test",
                ramble.application.ApplicationBase._inventory_file_name,
            )
        )
