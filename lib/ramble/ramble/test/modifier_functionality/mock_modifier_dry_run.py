# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.test.modifier_functionality.modifier_helpers as modifier_helpers
import ramble.workspace
from ramble.error import DirectiveError, InvalidModeError
from ramble.main import RambleCommand
from ramble.test.dry_run_helpers import SCOPES, dry_run_config

workspace = RambleCommand("workspace")


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
@pytest.mark.parametrize("modifier_mode", [None, "disabled"])  # Default mode
def test_gromacs_dry_run_mock_mods(
    mutable_mock_workspace_path,
    mutable_applications,
    mock_modifier,
    mock_modifiers,
    scope,
    modifier_mode,
    workspace_name,
):
    test_modifiers = [
        (scope, modifier_helpers.named_modifier(mock_modifier, modifier_mode)),
    ]

    expected_failures = {
        "multiple-modes-no-default": {"error": InvalidModeError, "msg": "Cannot auto determine"},
        "invalid-builtin-injection": {
            "error": DirectiveError,
            "msg": "has an invalid injection method of",
        },
    }

    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        dry_run_config("modifiers", test_modifiers, config_path, "gromacs", "water_bare")

        ws1._re_read()

        if modifier_mode != "disabled" and mock_modifier in expected_failures:
            with pytest.raises(
                expected_failures[mock_modifier]["error"],
                match=expected_failures[mock_modifier]["msg"],
            ):
                workspace("concretize", global_args=["-D", ws1.root])
        else:
            workspace("concretize", global_args=["-D", ws1.root])
            workspace("setup", "--dry-run", global_args=["-D", ws1.root])
            exp_script = os.path.join(
                ws1.experiment_dir, "gromacs", "water_bare", "test_exp", "execute_experiment"
            )

            assert os.path.isfile(exp_script)
