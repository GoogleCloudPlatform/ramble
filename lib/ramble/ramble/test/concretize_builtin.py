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

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_concretize_does_not_set_required(mutable_config, mutable_mock_workspace_path):
    """
    Verify that concretizing an application with required set to True
    does not insert a required statement into software dict.
    """

    test_config = """
ramble:
  variants:
    package_manager: spack
  variables:
    mpi_command: 'mpirun'
    batch_submit: '{execute_experiment}'
    partition: ['part1', 'part2']
    processes_per_node: ['16', '36']
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    wrfv4:
      variables:
        env_name: 'wrfv4'
      workloads:
        CONUS_12km:
          experiments:
            scaling_{n_nodes}_{partition}_{env_name}:
              success_criteria:
              - name: 'timing'
                mode: 'string'
                match: '.*Timing for main.*'
                file: '{experiment_run_dir}/rsl.out.0000'
              env_vars:
                set:
                  OMP_NUM_THREADS: '{n_threads}'
                  TEST_VAR: '1'
                append:
                - var-separator: ', '
                  vars:
                    TEST_VAR: 'add_var'
                - paths:
                    TEST_VAR: 'new_path'
                prepend:
                - paths:
                    TEST_VAR: 'pre_path'
                unset:
                - TEST_VAR
              variables:
                n_nodes: ['1', '2', '4', '8', '16']
              matrix:
              - n_nodes
  software:
    packages: {}
    environments: {}
"""

    import re

    workspace_name = "test_concretize_does_not_set_required"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws._re_read()

        ws.concretize()

        ws._re_read()

        req_test = True
        with open(config_path) as f:
            for line in f.readlines():
                if re.match(r"^[^#]*required", line):
                    req_test = False
                    break
            assert req_test
