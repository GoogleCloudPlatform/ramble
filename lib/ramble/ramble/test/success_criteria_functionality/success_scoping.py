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
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")
ramble_on = RambleCommand("on")


def test_disconnected_success(mock_applications, workspace_name):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
    processes_per_node: '1'
    n_threads: '1'
  applications:
    basic:
      workloads:
        working_wl:
          experiments:
            pass-experiment:
              variables:
                n_nodes: 1
              success_criteria:
              - name: always-pass
                mode: string
                match: '.*seconds.*'
            fail-experiment:
              variables:
                n_nodes: 1
              success_criteria:
              - name: always-fail
                mode: string
                match: 'Blarg'
  software:
    packages: {}
    environments: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        with open(config_path, "w+", encoding="utf-8") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", global_args=["-w", workspace_name])
        ramble_on(global_args=["-w", workspace_name])
        workspace(
            "analyze", "--where", "{experiment_index} == 1", global_args=["-w", workspace_name]
        )

        with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
            data = f.read()
            assert "Status = SUCCESS" in data

        workspace(
            "analyze", "--where", "{experiment_index} == 2", global_args=["-w", workspace_name]
        )

        with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
            data = f.read()
            assert "Status = FAILED" in data
