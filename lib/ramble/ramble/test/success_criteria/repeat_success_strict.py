# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")
ramble_on = RambleCommand("on")


def test_repeat_success_strict(mutable_config, mutable_mock_workspace_path, mock_applications):
    test_config = """
ramble:
  config:
    repeat_success_strict: False
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    basic:
      workloads:
        working_wl:
          experiments:
            test_exp:
              n_repeats: 2
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_repeat_success_strict"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", global_args=["-w", workspace_name])
        ramble_on(global_args=["-w", workspace_name])
        workspace("analyze", global_args=["-w", workspace_name])

        with open(os.path.join(ws.root, "results.latest.txt")) as f:
            data = f.read()
            assert "FAILED" not in data
            assert "summary::n_total_repeats = 2 repeats" in data
            assert "summary::n_successful_repeats = 2 repeats" in data

        # Write mock output to fail one of the experiments
        result_path = os.path.join(
            ws.experiment_dir, "basic", "working_wl", "test_exp.1", "test_exp.1.out"
        )
        with open(result_path, "w+") as f:
            f.write("")

        workspace("analyze", global_args=["-w", workspace_name])

        with open(os.path.join(ws.root, "results.latest.txt")) as f:
            data = f.read()
            assert "SUCCESS" in data
            assert "FAILED" in data
            assert "summary::n_total_repeats = 2 repeats" in data
            assert "summary::n_successful_repeats = 1 repeats" in data

        # Write mock output to fail the second experiment
        result_path = os.path.join(
            ws.experiment_dir, "basic", "working_wl", "test_exp.2", "test_exp.2.out"
        )
        with open(result_path, "w+") as f:
            f.write("")

        workspace("analyze", global_args=["-w", workspace_name])

        with open(os.path.join(ws.root, "results.latest.txt")) as f:
            data = f.read()
            assert "SUCCESS" not in data
            assert "summary::n_total_repeats" not in data
            assert "summary::n_successful_repeats" not in data
