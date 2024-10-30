# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import re
import os
import glob

import pytest

from ramble.test.dry_run_helpers import dry_run_config, search_files_for_string, SCOPES
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
def test_gromacs_dry_run_mock_mod_phase(
    mutable_mock_workspace_path, mutable_applications, mock_modifiers, scope
):
    workspace_name = "test_gromacs_dry_run_mock_mod_phase"

    test_modifiers = [
        (scope, modifier_helpers.named_modifier("mod-phase")),
    ]

    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        dry_run_config("modifiers", test_modifiers, config_path, "gromacs", "water_bare")

        ws1._re_read()

        workspace("concretize", global_args=["-D", ws1.root])
        workspace("setup", "--dry-run", global_args=["-D", ws1.root])
        out_files = glob.glob(os.path.join(ws1.log_dir, "**", "*.out"), recursive=True)

        out_file = os.path.join(ws1.log_dir, "setup.latest", "gromacs.water_bare.test_exp.out")

        found_make_experiments = False
        found_after_phase = False
        found_mod_phase = False
        mod_phase_regex = re.compile("Executing phase mod_phase")
        make_experiments_regex = re.compile("Executing phase make_experiments")
        after_make_experiments_regex = re.compile("Executing phase after_make_experiments")

        with open(out_file) as f:
            for line in f.readlines():
                if mod_phase_regex.search(line):
                    found_mod_phase = True

                if make_experiments_regex.search(line):
                    assert found_mod_phase
                    found_make_experiments = True

                if after_make_experiments_regex.search(line):
                    assert found_make_experiments
                    found_after_phase = True

        assert found_mod_phase
        assert found_after_phase

        expected_str = "Inside a phase: mod_phase"

        assert search_files_for_string(out_files, expected_str)

        expected_str = "Inside a phase: after_make_experiments"

        assert search_files_for_string(out_files, expected_str)
