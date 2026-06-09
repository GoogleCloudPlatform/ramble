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

workspace = RambleCommand("workspace")


@pytest.mark.maybeslow
def test_anti_match_criteria(mutable_config, mutable_mock_workspace_path, mock_applications):
    ws_name = "test_anti_match_criteria"
    with ramble.workspace.create(ws_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        dry_run_config(
            "success_criteria",
            [
                (
                    SCOPES.application,
                    {"name": "anti_match_criterion", "mode": "string", "anti_match": "Error:"},
                )
            ],
            config_path,
            "basic",
            "test_wl",
        )
        ws._re_read()

        workspace("setup", "--dry-run", global_args=["-w", ws_name])
        result_path = os.path.join(
            ws.experiment_dir, "basic", "test_wl", "test_exp", "test_exp.out"
        )

        with open(result_path, "w", encoding="utf-8") as f:
            f.write("1.2seconds\n")
        workspace("analyze", global_args=["-w", ws_name])
        with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
            content = f.read()
            assert "Status = SUCCESS" in content
            assert "1.2" in content

        with open(result_path, "a", encoding="utf-8") as f:
            f.write("Error: invalid result\n")
        workspace("analyze", global_args=["-w", ws_name])
        with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
            content = f.read()
            assert "Status = FAILED" in content
