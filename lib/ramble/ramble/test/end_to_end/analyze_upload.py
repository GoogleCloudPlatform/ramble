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
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


@pytest.mark.maybeslow
def test_analyze_upload():
    test_config = """
ramble:
  config:
    upload:
      uri: fake-dataset
      type: PrintOnly
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '1'
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test:
              variables:
                n_nodes: '1'
  software:
    packages: {}
    environments: {}
"""
    ws_name = "test_analyze_upload"
    ws = ramble.workspace.create(ws_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    workspace("setup", "--dry-run", global_args=["-w", ws_name])
    exp_out = os.path.join(ws.experiment_dir, "hostname", "local", "test", "test.out")
    with open(exp_out, "w") as f:
        f.write("test-user.c.googlers.com\n")

    workspace("analyze", "--upload", global_args=["-w", ws_name])

    analyze_log = os.path.join(ws.log_dir, "analyze.latest.out")

    with open(analyze_log) as f:
        content = f.read()
        assert "Uploading results to fake-dataset" in content
        assert "The PrintOnly uploader only logs" in content
        assert "1 experiment(s) would be uploaded" in content
        assert "1 fom(s) would be uploaded" in content
        assert "test-user.c.googlers.com" in content
