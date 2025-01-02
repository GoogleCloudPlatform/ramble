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
    "value,formula,result",
    [
        ("1.0 seconds", "{value} > 0.5", "SUCCESS"),
        ("1.0 seconds", "{value} > 1.5", "FAILED"),
        ("1.0 seconds", "{value} < 0.5", "FAILED"),
        ("1.0 seconds", "{value} < 1.5", "SUCCESS"),
        ("1.0 seconds", "{value} >= 0.5", "SUCCESS"),
        ("1.0 seconds", "{value} >= 1.5", "FAILED"),
        ("1.0 seconds", "{value} >= 1", "SUCCESS"),
        ("1.0 seconds", "{value} <= 0.5", "FAILED"),
        ("1.0 seconds", "{value} <= 1.5", "SUCCESS"),
        ("1.0 seconds", "{value} == 1.0", "SUCCESS"),
        ("1.1 seconds", "{value} == 1.0", "FAILED"),
        ("1.1 seconds", "{value} != 1.0", "SUCCESS"),
        ("1.1 seconds", "{value} != 1.1", "FAILED"),
        ("1.0 seconds", "{value} > 0.5 and {value} != 1.1", "SUCCESS"),
        ("1.0 seconds", "{value} > 0.5 and {value} != 1.0", "FAILED"),
        ("1.0 seconds", "{value} < 0.5 or {value} != 1.1", "SUCCESS"),
        ("1.0 seconds", "{value} < 0.5 or {value} != 1.0", "FAILED"),
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
def test_success_fom_comparison(
    mutable_config, mutable_mock_workspace_path, mock_applications, value, formula, result, scope
):

    success_criteria_definitions = [
        (
            scope,
            {
                "name": "test_criteria",
                "mode": "fom_comparison",
                "fom_name": "test_fom",
                "formula": formula,
            },
        )
    ]

    workspace_name = "test_success_fom_comparison"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        dry_run_config(
            "success_criteria", success_criteria_definitions, config_path, "basic", "test_wl"
        )
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
