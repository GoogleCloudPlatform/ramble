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
from ramble.util import json_util
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


def test_repeat_analyze_where_experiment_status(mock_applications, make_workspace_from_config):
    # Test strict mode (default: repeat_success_strict is True)
    test_config = """
ramble:
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

    # Fail repeat child 1
    result_path = os.path.join(
        ws.experiment_dir, "basic", "working_wl", "test_exp.1", "test_exp.1.out"
    )
    with open(result_path, "w+", encoding="utf-8") as f:
        f.write("")

    # First analyze without filters so child statuses are recorded
    workspace("analyze", "-f", "json", "text", global_args=["-w", ws_name])

    # Now analyze filtering for FAILED
    workspace(
        "analyze",
        "-f",
        "json",
        "text",
        "--where",
        "'{experiment_status}' == 'FAILED'",
        global_args=["-w", ws_name],
    )

    with open(os.path.join(ws.results_dir, "results.latest.json"), encoding="utf-8") as f:
        data = json_util.load(f)
        exp_names = [exp["name"] for exp in data["experiments"]]
        # In strict mode, since child 1 failed, both parent and child 1 must be present as FAILED
        assert "basic.working_wl.test_exp" in exp_names
        assert "basic.working_wl.test_exp.1" in exp_names
        assert "basic.working_wl.test_exp.2" not in exp_names

    with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
        txt_data = f.read()
        assert "Experiment basic.working_wl.test_exp figures of merit:" in txt_data
        assert "Experiment basic.working_wl.test_exp.1 figures of merit:" in txt_data
        assert "Experiment basic.working_wl.test_exp.2 figures of merit:" not in txt_data

    # Now analyze filtering for SUCCESS
    workspace(
        "analyze",
        "-f",
        "json",
        "text",
        "--where",
        "'{experiment_status}' == 'SUCCESS'",
        global_args=["-w", ws_name],
    )

    with open(os.path.join(ws.results_dir, "results.latest.json"), encoding="utf-8") as f:
        data = json_util.load(f)
        exp_names = [exp["name"] for exp in data["experiments"]]
        # In strict mode, parent is FAILED, so only child 2 is SUCCESS
        assert "basic.working_wl.test_exp" not in exp_names
        assert "basic.working_wl.test_exp.1" not in exp_names
        assert "basic.working_wl.test_exp.2" in exp_names


def test_repeat_analyze_where_experiment_status_loose(
    mock_applications, make_workspace_from_config
):
    # Test loose mode (repeat_success_strict is False)
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

    # Fail repeat child 1
    result_path = os.path.join(
        ws.experiment_dir, "basic", "working_wl", "test_exp.1", "test_exp.1.out"
    )
    with open(result_path, "w+", encoding="utf-8") as f:
        f.write("")

    # First analyze without filters so child statuses are recorded
    workspace("analyze", "-f", "json", "text", global_args=["-w", ws_name])

    # In loose mode, child 2 succeeded, so parent is SUCCESS
    workspace(
        "analyze",
        "-f",
        "json",
        "text",
        "--where",
        "'{experiment_status}' == 'SUCCESS'",
        global_args=["-w", ws_name],
    )

    with open(os.path.join(ws.results_dir, "results.latest.json"), encoding="utf-8") as f:
        data = json_util.load(f)
        exp_names = [exp["name"] for exp in data["experiments"]]
        # In loose mode, parent and child 2 are SUCCESS
        assert "basic.working_wl.test_exp" in exp_names
        assert "basic.working_wl.test_exp.2" in exp_names
        assert "basic.working_wl.test_exp.1" not in exp_names

    # Filter for FAILED: only child 1 is FAILED, parent is SUCCESS
    workspace(
        "analyze",
        "-f",
        "json",
        "text",
        "--where",
        "'{experiment_status}' == 'FAILED'",
        global_args=["-w", ws_name],
    )

    with open(os.path.join(ws.results_dir, "results.latest.json"), encoding="utf-8") as f:
        data = json_util.load(f)
        exp_names = [exp["name"] for exp in data["experiments"]]
        assert "basic.working_wl.test_exp" not in exp_names
        assert "basic.working_wl.test_exp.1" in exp_names
        assert "basic.working_wl.test_exp.2" not in exp_names
