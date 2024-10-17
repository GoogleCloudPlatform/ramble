# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import glob

import pytest

from ramble.test.dry_run_helpers import dry_run_config, search_files_for_string, SCOPES
import ramble.test.modifier_functionality.modifier_helpers as modifier_helpers

import ramble.workspace
from ramble.main import RambleCommand

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
def test_gromacs_dry_run_mock_spack_mod(
    mutable_mock_workspace_path, mutable_applications, mock_modifiers, scope
):
    workspace_name = "test_gromacs_dry_run_mock_spack_mod"

    test_modifiers = [
        (scope, modifier_helpers.named_modifier("spack-mod")),
    ]

    software_tests = [
        ("gromacs", "mod_package1@1.1"),
        ("gromacs", "mod_package2@1.1"),
        ("gromacs", "gromacs"),
    ]

    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        dry_run_config("modifiers", test_modifiers, config_path, "gromacs", "water_bare")

        ws1._re_read()

        workspace("concretize", global_args=["-D", ws1.root])
        workspace("setup", "--dry-run", global_args=["-D", ws1.root])
        out_files = glob.glob(os.path.join(ws1.log_dir, "**", "*.out"), recursive=True)

        expected_str = "with args: ['--reuse', 'mod_compiler@1.1 target=x86_64']"

        assert search_files_for_string(out_files, expected_str)

        expected_str = "with args: ['list', 'not-a-package']"

        assert search_files_for_string(out_files, expected_str)

        expected_str = "with args: ['info', 'zlib']"

        assert search_files_for_string(out_files, expected_str)

        # Test software directories
        software_base_dir = os.path.join(ws1.software_dir, "spack")

        modifier_helpers.check_software_env(software_base_dir, software_tests)
