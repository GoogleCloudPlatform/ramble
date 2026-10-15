# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")
ramble_on = RambleCommand("on")


def test_success_function(mock_applications, make_workspace_from_config):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    success-function:
      workloads:
        test_wl:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    ws, ws_name = make_workspace_from_config(test_config)

    workspace("setup", global_args=["-w", ws_name])
    ramble_on(global_args=["-w", ws_name])
    workspace("analyze", global_args=["-w", ws_name])

    with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
        data = f.read()
        assert "FAILED" in data
        assert "0.9 s" in data
