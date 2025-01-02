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
import ramble.config
import ramble.software_environments
import ramble.namespace
from ramble.main import RambleCommand
from ramble.test.dry_run_helpers import dry_run_config, SCOPES


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "value,result",
    [
        ("1.0 seconds\nExperiment status: SUCCESS", "SUCCESS"),
        ("1.0 seconds\nExperiment status: FAILED", "FAILED"),
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
):

    modifier = [
        (scope, {"name": "success-criteria"}),
    ]

    workspace_name = "test_success_modifier"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        dry_run_config("modifiers", modifier, config_path, "basic", "test_wl")
        ws._re_read()

        workspace("concretize", global_args=["-w", workspace_name])
        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        # Write mock output data:
        result_path = os.path.join(
            ws.experiment_dir, "basic", "test_wl", "test_exp", "test_exp.out"
        )
        with open(result_path, "w+") as f:
            f.write(value)

        workspace("analyze", global_args=["-w", workspace_name])

        with open(os.path.join(ws.root, "results.latest.txt")) as f:
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
  spack:
    packages: {}
    environments: {}
  modifiers:
  - name: success-criteria
"""
    workspace_name = "test-modifier-success-criteria"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    workspace("setup", "--dry-run", global_args=["-w", workspace_name])

    exp1_out = os.path.join(ws.experiment_dir, "basic", "working_wl", "test1", "test1.out")
    with open(exp1_out, "w+") as f:
        f.write("0.25 seconds\nExperiment status: SUCCESS\n")
    exp2_out = os.path.join(ws.experiment_dir, "basic", "working_wl", "test2", "test2.out")
    with open(exp2_out, "w+") as f:
        f.write("0.35 seconds\nExperiment status: SUCCESS\n")

    workspace("analyze", global_args=["-w", workspace_name])
    result_file = os.path.join(ws.root, "results.latest.txt")

    with open(result_file) as f:
        content = f.read()
        assert "FAILED" not in content
        assert "default (null) context figures of merit" in content
        assert "test_fom = 0.25 s" in content
        assert "test_fom = 0.35 s" in content
