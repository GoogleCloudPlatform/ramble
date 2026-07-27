# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.main import RambleCommand
from ramble.util.foms import SummaryFoms

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")
ramble_on = RambleCommand("on")


def test_repeat_success_strict(mock_applications, make_workspace_from_config):
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
    ws, ws_name = make_workspace_from_config(test_config)

    workspace("setup", global_args=["-w", ws_name])
    ramble_on(global_args=["-w", ws_name])
    workspace("analyze", global_args=["-w", ws_name])

    with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
        data = f.read()
        assert "FAILED" not in data
        assert f"summary::{SummaryFoms.N_TOTAL.value} = 2 repeats" in data
        assert f"summary::{SummaryFoms.N_SUCCESS.value} = 2 repeats" in data

    # Write mock output to fail one of the experiments
    result_path = os.path.join(
        ws.experiment_dir, "basic", "working_wl", "test_exp.1", "test_exp.1.out"
    )
    with open(result_path, "w+", encoding="utf-8") as f:
        f.write("")

    workspace("analyze", global_args=["-w", ws_name])

    with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
        data = f.read()
        assert "SUCCESS" in data
        assert "FAILED" in data
        assert f"summary::{SummaryFoms.N_TOTAL.value} = 2 repeats" in data
        assert f"summary::{SummaryFoms.N_SUCCESS.value} = 1 repeats" in data

    # Write mock output to fail the second experiment
    result_path = os.path.join(
        ws.experiment_dir, "basic", "working_wl", "test_exp.2", "test_exp.2.out"
    )
    with open(result_path, "w+", encoding="utf-8") as f:
        f.write("")

    workspace("analyze", global_args=["-w", ws_name])

    with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
        data = f.read()
        assert "SUCCESS" not in data
        assert f"summary::{SummaryFoms.N_TOTAL.value}" not in data
        assert f"summary::{SummaryFoms.N_SUCCESS.value}" not in data
