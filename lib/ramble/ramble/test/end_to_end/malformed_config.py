# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import pytest

import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


def test_missing_config_keys(make_workspace_from_config):
    test_config = """
amble:
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: 1
    n_nodes: 1
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test: {}
"""
    ws, ws_name = make_workspace_from_config(test_config)

    with pytest.raises(
        ramble.workspace.RambleActiveWorkspaceError,
        match="ramble.yaml needs to contain at least one of the required keys",
    ):
        workspace("info", global_args=["-w", ws_name])
