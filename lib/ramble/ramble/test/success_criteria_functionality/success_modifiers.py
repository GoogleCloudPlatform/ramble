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
from ramble.test.dry_run_helpers import SCOPES, dry_run_config

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "value,result",
    [
        ("1.0 seconds\nExperiment status: SUCCESS", "SUCCESS"),
        ("1.0 seconds\nExperiment status: FAILED", "FAILED"),
    ],
)
@pytest.mark.parametrize(
    "scope",
    [
        SCOPES.workspace,
        SCOPES.application,
        SCOPES.workload,
        SCOPES.experiment,
    ],
)
def test_success_modifier(
    mutable_config,
    mutable_mock_workspace_path,
    mock_applications,
    mock_modifiers,
    value,
    result,
    scope,
    workspace_name,
):

    modifier = [
        (scope, {"name": "success-criteria"}),
    ]

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        dry_run_config("modifiers", modifier, config_path, "basic", "test_wl")
        ws._re_read()

        workspace("concretize", global_args=["-w", workspace_name])
        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        # Write mock output data:
        result_path = os.path.join(
            ws.experiment_dir, "basic", "test_wl", "test_exp", "test_exp.out"
        )
        with open(result_path, "w+", encoding="utf-8") as f:
            f.write(value)

        workspace("analyze", global_args=["-w", workspace_name])

        with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
            data = f.read()
            assert result in data


def test_success_criteria_with_multiple_experiments(mock_applications, mock_modifiers):
    test_config = """
ramble:
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '1'
  applications:
    basic:
      workloads:
        working_wl:
          experiments:
            test1:
              variables:
                n_nodes: '1'
            test2:
              variables:
                n_nodes: '1'
  software:
    packages: {}
    environments: {}
  modifiers:
  - name: success-criteria
"""
    workspace_name = "test-modifier-success-criteria"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

    with open(config_path, "w+", encoding="utf-8") as f:
        f.write(test_config)

    ws._re_read()

    workspace("setup", "--dry-run", global_args=["-w", workspace_name])

    exp1_out = os.path.join(ws.experiment_dir, "basic", "working_wl", "test1", "test1.out")
    with open(exp1_out, "w+", encoding="utf-8") as f:
        f.write("0.25 seconds\nExperiment status: SUCCESS\n")
    exp2_out = os.path.join(ws.experiment_dir, "basic", "working_wl", "test2", "test2.out")
    with open(exp2_out, "w+", encoding="utf-8") as f:
        f.write("0.35 seconds\nExperiment status: SUCCESS\n")

    workspace("analyze", global_args=["-w", workspace_name])
    result_file = os.path.join(ws.results_dir, "results.latest.txt")

    with open(result_file, encoding="utf-8") as f:
        content = f.read()
        assert "FAILED" not in content
        assert "default (null) context figures of merit" in content
        assert "test_fom = 0.25 s" in content
        assert "test_fom = 0.35 s" in content


def test_success_criteria_preserves_terminal_failures(mock_applications, mock_modifiers):
    test_config = """
ramble:
  variables:
    mpi_command: ''
    batch_submit: '{execute_experiment}'
    processes_per_node: '1'
  applications:
    basic:
      workloads:
        working_wl:
          experiments:
            test_cancelled:
              variables:
                n_nodes: '1'
            test_timeout:
              variables:
                n_nodes: '1'
  modifiers:
  - name: success-criteria
"""
    workspace_name = "test-preserved-terminal-failures"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()
    workspace("setup", "--dry-run", global_args=["-w", workspace_name])

    import spack.util.spack_json as sjson

    # Write mock output data that fails success criteria:
    exp1_dir = os.path.join(ws.experiment_dir, "basic", "working_wl", "test_cancelled")
    with open(os.path.join(exp1_dir, "test_cancelled.out"), "w+") as f:
        f.write("0.25 seconds\n")
    with open(os.path.join(exp1_dir, "ramble_status.json"), "w+") as f:
        sjson.dump({"experiment_status": "CANCELLED"}, f)

    exp2_dir = os.path.join(ws.experiment_dir, "basic", "working_wl", "test_timeout")
    with open(os.path.join(exp2_dir, "test_timeout.out"), "w+") as f:
        f.write("0.35 seconds\n")
    with open(os.path.join(exp2_dir, "ramble_status.json"), "w+") as f:
        sjson.dump({"experiment_status": "TIMEOUT"}, f)

    workspace(
        "analyze",
        "--formats",
        "json",
        global_args=["-w", workspace_name],
    )
    result_file = os.path.join(ws.results_dir, "results.latest.json")

    with open(result_file) as f:
        cache_dict = sjson.load(f)
        for exp in cache_dict["experiments"]:
            if "cancelled" in exp["name"]:
                assert exp["EXPERIMENT_STATUS"] == "CANCELLED"
                assert exp["RAMBLE_STATUS"] == "FAILED"
            if "timeout" in exp["name"]:
                assert exp["EXPERIMENT_STATUS"] == "TIMEOUT"
                assert exp["RAMBLE_STATUS"] == "FAILED"
