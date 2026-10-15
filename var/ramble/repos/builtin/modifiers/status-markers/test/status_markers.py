# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)


def test_status_markers(request):
    ws_name = request.node.name
    test_config = """
ramble:
  modifiers:
  - name: status-markers
  variables:
    processes_per_node: 1
    n_nodes: 1
    mpi_command: ''
    batch_submit: '{execute_experiment}'
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test: {}
"""
    ws = ramble.workspace.create(ws_name)
    ws.write()
    config_path = os.path.join(
        ws.config_dir, ramble.workspace.CONFIG_FILE_NAME
    )
    with open(config_path, "w+", encoding="utf-8") as f:
        f.write(test_config)
    ws._re_read()
    workspace("setup", "--dry-run", global_args=["-D", ws.root])
    run_dir = os.path.join(ws.experiment_dir, "hostname", "local", "test")
    with open(
        os.path.join(run_dir, "execute_experiment"), encoding="utf-8"
    ) as f:
        content = f.read()
        assert (
            f'echo "Started" > "{os.path.join(ws.root, "status.hostname.local.test.started")}" 2>&1'
            in content
        )
        assert (
            f'rm -f "{os.path.join(ws.root, "status.hostname.local.test.finished")}"'
            in content
        )
        assert (
            f'echo "Finished" > "{os.path.join(ws.root, "status.hostname.local.test.finished")}" 2>&1'
            in content
        )
