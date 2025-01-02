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
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


def test_pip():
    test_config = """
ramble:
  variants:
    package_manager: pip
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: 1
    n_ranks: 1
  applications:
    pip-test:
      workloads:
        import:
          experiments:
            test_import: {}
  software:
    packages:
      requests:
        pkg_spec: requests>=2.31.0
      semver:
        pkg_spec: semver
    environments:
      pip-test:
        packages:
        - requests
        - semver
"""
    workspace_name = "test-pip-pkgman"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    workspace("setup", "--dry-run", global_args=["-w", workspace_name])

    setup_out = os.path.join(ws.log_dir, "setup.latest", "pip-test.import.test_import.out")
    with open(setup_out) as f:
        content = f.read()
        assert "Executing phase software_create_env" in content
        assert "Executing phase software_install" in content
        assert "pip/pip-test/requirements.txt" in content
        assert "freeze" in content
