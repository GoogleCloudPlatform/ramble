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


def test_get_file_path(mock_applications, mock_file_auto_create):
    test_config = """
ramble:
  config:
    disable_progress_bar: true
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '1'
  applications:
    file-open:
      workloads:
        test_wl:
          experiments:
            test:
              variables:
                n_ranks: '1'
  spack:
    packages: {}
    environments: {}
"""
    workspace_name = "test-get-file-path"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    workspace("setup", "--dry-run", global_args=["-w", workspace_name])

    test_out = os.path.join(ws.log_dir, "setup.latest", "file-open.test_wl.test.out")
    with open(test_out) as f:
        content = f.read()
        # When in dry-run, the test mock pretends the file exists
        assert "Config loaded from dry-run/path/to/file-open/my/config.yaml" in content
