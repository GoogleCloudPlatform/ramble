# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.test.dry_run_helpers import dry_run_config, SCOPES
import ramble.test.modifier_functionality.modifier_helpers as modifier_helpers

import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")


def test_layered_variable_modifications(
    mutable_mock_workspace_path, mutable_applications, mock_modifiers
):
    workspace_name = "test_gromacs_dry_run_mock_spack_mod"

    test_modifiers = [
        (SCOPES.experiment, modifier_helpers.named_modifier("test-mod")),
        (SCOPES.experiment, modifier_helpers.named_modifier("test-mod-2")),
    ]

    test_template = """
{test_var_mod}
"""

    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)
        template_path = os.path.join(ws1.config_dir, "test.tpl")

        with open(template_path, "w+") as f:
            f.write(test_template)

        dry_run_config("modifiers", test_modifiers, config_path, "gromacs", "water_bare")

        ws1._re_read()

        workspace("concretize", global_args=["-D", ws1.root])
        workspace("setup", "--dry-run", global_args=["-D", ws1.root])

        rendered_template = os.path.join(
            ws1.experiment_dir, "gromacs", "water_bare", "test_exp", "test"
        )
        assert os.path.exists(rendered_template)

        with open(rendered_template) as f:
            data = f.read()
            assert "test-mod-2-append" in data
            assert "test-mod-append" in data
