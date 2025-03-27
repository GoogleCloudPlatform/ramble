# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import ramble.test.modifier_functionality.modifier_helpers as modifier_helpers
import ramble.workspace
from ramble.main import RambleCommand
from ramble.test.dry_run_helpers import SCOPES, dry_run_config

workspace = RambleCommand("workspace")


def test_repeated_variable_modifications(
    mutable_mock_workspace_path, mutable_applications, mock_modifiers, request
):
    workspace_name = request.node.name

    test_modifiers = [
        (SCOPES.experiment, modifier_helpers.named_modifier("repeat-var-mod")),
    ]

    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        dry_run_config("modifiers", test_modifiers, config_path, "gromacs", "water_bare")

        ws1._re_read()

        workspace("concretize", global_args=["-D", ws1.root])
        workspace("setup", "--dry-run", global_args=["-D", ws1.root])

        rendered_template = os.path.join(
            ws1.experiment_dir, "gromacs", "water_bare", "test_exp", "execute_experiment"
        )
        assert os.path.exists(rendered_template)

        with open(rendered_template) as f:
            data = f.read()
            assert "prefix_mpi_command" in data
            assert "suffix_mpi_command" in data
