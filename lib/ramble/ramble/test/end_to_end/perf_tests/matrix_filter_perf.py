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

pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")
workspace = RambleCommand("workspace")


@pytest.mark.perf
@pytest.mark.maybeslow
def test_matrix_filter_perf(make_workspace_from_config, ramble_benchmark):
    # Create a matrix of 10000 experiments, but exclude 9999 of them.
    # This test is to monitor the efficiency of the filtering.
    test_config = (
        """
ramble:
  variables:
    mpi_command: ''
    batch_submit: '{execute_experiment}'
    processes_per_node: 1
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test_{n_nodes}_{matrix_var}:
              variables:
                n_nodes: ["""
        + ", ".join([f"'{i}'" for i in range(1, 101)])
        + """]
                matrix_var: ["""
        + ", ".join([f"'{i}'" for i in range(1, 101)])
        + """]
              matrix:
              - n_nodes
              - matrix_var
              exclude:
                where:
                - '{n_nodes} != 1 or {matrix_var} != 1'
"""
    )
    ws, ws_name = make_workspace_from_config(test_config)

    ramble_benchmark(workspace, "setup", "--dry-run", global_args=["-w", ws_name])

    exp_dir = os.path.join(ws.root, "experiments", "hostname", "local", "test_1_1")
    assert os.path.isdir(exp_dir)

    # Pick one to assert the filtering is functional
    exp_dir = os.path.join(ws.root, "experiments", "hostname", "local", "test_100_100")
    assert not os.path.isdir(exp_dir)
