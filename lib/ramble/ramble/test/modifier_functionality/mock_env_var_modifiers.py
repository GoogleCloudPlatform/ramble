# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.test.dry_run_helpers import dry_run_config, SCOPES
import ramble.test.modifier_functionality.modifier_helpers as modifier_helpers

import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "scope",
    [
        SCOPES.workspace,
        SCOPES.application,
        SCOPES.workload,
        SCOPES.experiment,
    ],
)
@pytest.mark.parametrize(
    "factory,answer",
    [
        (
            modifier_helpers.env_var_append_paths_modifier,
            modifier_helpers.env_var_append_paths_modifier_answer,
        ),
        (
            modifier_helpers.env_var_append_vars_modifier,
            modifier_helpers.env_var_append_vars_modifier_answer,
        ),
        (
            modifier_helpers.env_var_prepend_paths_modifier,
            modifier_helpers.env_var_prepend_paths_modifier_answer,
        ),
        (modifier_helpers.env_var_set_modifier, modifier_helpers.env_var_set_modifier_answer),
        (modifier_helpers.env_var_unset_modifier, modifier_helpers.env_var_unset_modifier_answer),
    ],
)
def test_gromacs_dry_run_mock_env_vars_mod(
    mutable_mock_workspace_path, mutable_applications, mock_modifiers, scope, factory, answer
):
    workspace_name = "test_gromacs_dry_run_mock_env_vars_mod"

    test_modifiers = [
        (scope, factory()),
    ]

    software_tests, expected_strs = answer()

    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        dry_run_config("modifiers", test_modifiers, config_path, "gromacs", "water_bare")

        ws1._re_read()

        workspace("concretize", global_args=["-D", ws1.root])
        workspace("setup", "--dry-run", global_args=["-D", ws1.root])

        # Test software directories
        software_base_dir = os.path.join(ws1.software_dir, "spack")

        modifier_helpers.check_software_env(software_base_dir, software_tests)

        exp_script = os.path.join(
            ws1.experiment_dir, "gromacs", "water_bare", "test_exp", "execute_experiment"
        )

        modifier_helpers.check_execute_script(exp_script, expected_strs)
