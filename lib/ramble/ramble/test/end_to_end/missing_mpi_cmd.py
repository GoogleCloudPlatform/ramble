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


def test_missing_mpi_cmd():
    test_config = """
ramble:
  variants:
    package_manager: None
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '1'
    hostlist: 'foo'
  applications:
    gromacs:
      workloads:
        water_bare:
          experiments:
            multi-node-test:
              variables:
                n_ranks: '3'
            single-node-test:
              variables:
                n_nodes: '1'
"""
    workspace_name = "test-missing-mpi-cmd"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    workspace("setup", "--dry-run", global_args=["-w", workspace_name])

    single_setup_out = os.path.join(
        ws.log_dir, "setup.latest", "gromacs.water_bare.single-node-test.out"
    )
    with open(single_setup_out) as f:
        content = f.read()
        assert "Warning:" not in content

    multi_setup_out = os.path.join(
        ws.log_dir, "setup.latest", "gromacs.water_bare.multi-node-test.out"
    )
    with open(multi_setup_out) as f:
        content = f.read()
        assert "Warning:" in content
        assert "requires a non-empty `mpi_command` variable" in content
