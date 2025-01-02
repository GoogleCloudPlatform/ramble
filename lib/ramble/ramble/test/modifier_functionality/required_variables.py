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
import ramble.experiment_set
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "test_name,mode,expect_error",
    [
        (
            "standard_require_hostlist",
            "standard",
            ramble.experiment_set.RambleVariableDefinitionError,
        ),
        ("local_no_require_hostlist", "local", None),
    ],
)
def test_required_variables(
    test_name, mode, expect_error, mutable_mock_workspace_path, mutable_applications
):
    workspace_name = test_name

    test_config = f"""
ramble:
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {{execute_experiment}}'
    processes_per_node: 1
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test:
              variables:
                n_nodes: 1
  modifiers:
  - name: gcp-metadata
    mode: {mode}
"""

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws._re_read()

        if expect_error:
            with pytest.raises(expect_error):
                workspace("setup", "--dry-run", global_args=["-D", ws.root])
        else:
            workspace("setup", "--dry-run", global_args=["-D", ws.root])
