# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.test.dry_run_helpers import *
from ramble.test.modifier_functionality.modifier_helpers import *
import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand('workspace')


@pytest.mark.parametrize(
    'scope',
    [
        SCOPES.workspace,
        SCOPES.application,
        SCOPES.workload,
        SCOPES.experiment,
    ]
)
def test_gromacs_dry_run_mock_spack_mod(mutable_mock_workspace_path,
                                        mutable_applications,
                                        mock_modifiers,
                                        scope):
    workspace_name = 'test_gromacs_dry_run_mock_spack_mod'

    test_modifiers = [
        (scope, named_modifier('spack-mod')),
    ]

    software_tests = [
        ('gromacs.water_bare', 'mod_package1@1.1'),
        ('gromacs.water_bare', 'mod_package2@1.1'),
        ('gromacs.water_bare', 'gromacs'),
    ]

    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        dry_run_config('modifiers', test_modifiers, config_path, 'gromacs', 'water_bare')

        ws1._re_read()

        workspace('concretize', global_args=['-D', ws1.root])
        output = workspace('setup', '--dry-run', global_args=['-D', ws1.root])

        expected_str = "with args: ['install', '--reuse', 'mod_compiler@1.1 target=x86_64']"

        assert expected_str in output

        # Test software directories
        software_base_dir = ws1.software_dir

        check_software_env(software_base_dir, software_tests)
