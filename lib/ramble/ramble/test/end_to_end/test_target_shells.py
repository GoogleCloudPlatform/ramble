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
from ramble.main import RambleCommand, RambleCommandError

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "configured_shell,expect_error",
    [
        ("csh", True),
        ("bash", False),
    ],
)
def test_target_shells_directive(configured_shell, expect_error):
    test_config = f"""
ramble:
  variables:
    mpi_command: ''
    batch_submit: '{{execute_experiment}}'
    processes_per_node: 1
    n_ranks: 1
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test: {{}}
  modifiers:
  # This requires bash shell
  - name: wait-for-bg-jobs
  config:
    shell: {configured_shell}
  software:
    packages: {{}}
    environments: {{}}
"""

    ws_name = f"test_{configured_shell}"
    ws = ramble.workspace.create(ws_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    if expect_error:
        with pytest.raises(RambleCommandError):
            workspace("setup", "--dry-run", global_args=["-w", ws_name])
    else:
        workspace("setup", "--dry-run", global_args=["-w", ws_name])
