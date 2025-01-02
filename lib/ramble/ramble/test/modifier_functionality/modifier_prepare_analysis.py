# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import re

import pytest

from ramble.test.dry_run_helpers import dry_run_config, SCOPES
import ramble.test.modifier_functionality.modifier_helpers as modifier_helpers

import ramble.workspace
from ramble.main import RambleCommand

config = RambleCommand("config")
workspace = RambleCommand("workspace")
on_cmd = RambleCommand("on")


@pytest.mark.long
@pytest.mark.parametrize(
    "scope",
    [
        SCOPES.workspace,
        SCOPES.application,
        SCOPES.workload,
        SCOPES.experiment,
    ],
)
def test_basic_dry_run_mock_prepare_analysis_mod(
    mutable_mock_workspace_path, mock_applications, mock_modifiers, scope
):
    workspace_name = "test_basic_dry_run_mock_prepare_analysis_mod"

    test_modifiers = [(scope, modifier_helpers.named_modifier("prepare-analysis"))]

    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        dry_run_config(
            "modifiers", test_modifiers, config_path, "basic", "working_wl", batch_cmd=""
        )

        ws1._re_read()
        ws_args = ["-D", ws1.root]

        workspace("concretize", global_args=ws_args)
        workspace("setup", global_args=ws_args)
        on_cmd(global_args=ws_args)
        workspace("analyze", global_args=ws_args)

        expected_regex = re.compile(".*This test worked")
        found_str = False
        with open(os.path.join(ws1.root, "results.latest.txt")) as f:
            for line in f.readlines():
                if expected_regex.match(line):
                    found_str = True

        assert found_str
