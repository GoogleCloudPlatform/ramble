# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import glob

import pytest

import llnl.util.tty as tty

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


def _setup_workspace(ws_name):
    test_config = """
ramble:
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
    ws = ramble.workspace.create(ws_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    workspace("setup", "--dry-run", global_args=["-w", ws_name])
    exp_out = os.path.join(ws.experiment_dir, "hostname", "local", "test", "test.out")
    with open(exp_out, "w+") as f:
        f.write("test-user.c.googlers.com\n")
    return ws


def test_analyze_fom_output():
    workspace_name = "test-fom-output"
    ws = _setup_workspace(workspace_name)

    workspace("analyze", "-p", global_args=["-w", workspace_name])
    result_file = glob.glob(os.path.join(ws.root, "results.latest.txt"))[0]

    with open(result_file) as f:
        content = f.read()
        assert "default (null) context figures of merit" in content
        assert "possible hostname = test-user.c.googlers.com" in content


def test_analyze_print(monkeypatch):
    workspace_name = "test-analyze-print"
    _setup_workspace(workspace_name)

    msg_list = []

    def _msg(msg, *args, **kwargs):
        msg_list.append(msg)

    # Assert whether the print is present or not
    monkeypatch.setattr(tty, "msg", _msg)

    workspace("analyze", global_args=["-w", workspace_name])
    assert not any(m.startswith("Results from the analysis pipeline") for m in msg_list)

    msg_list = []
    workspace("analyze", "-p", global_args=["-w", workspace_name])
    assert any(m.startswith("Results from the analysis pipeline") for m in msg_list)
