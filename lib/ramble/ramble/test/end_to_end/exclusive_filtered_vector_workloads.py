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
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_exclusive_filtered_vector_workloads(mutable_config, mutable_mock_workspace_path):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    hostname:
      workloads:
        '{application_workload}':
          experiments:
            simple_test:
              variables:
                application_workload: ['parallel' ,'serial', 'local']
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_exclusive_filtered_vector_workloads"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws._re_read()

        workspace(
            "setup",
            "--dry-run",
            "--exclude-where",
            '"{workload_name}" == "serial"',
            global_args=["-w", workspace_name],
        )
        workspace(
            "analyze",
            "--exclude-where",
            '"{workload_name}" == "serial"',
            global_args=["-w", workspace_name],
        )
        workspace(
            "archive",
            "--exclude-where",
            '"{workload_name}" == "serial"',
            global_args=["-w", workspace_name],
        )

        experiment_root = ws.experiment_dir
        expected_workloads = ["parallel", "local"]
        for workload in expected_workloads:
            exp1_dir = os.path.join(experiment_root, "hostname", workload, "simple_test")
            exp1_script = os.path.join(exp1_dir, "execute_experiment")
            assert os.path.isfile(exp1_script)

        not_expected_workloads = ["serial"]
        for workload in not_expected_workloads:
            exp1_dir = os.path.join(experiment_root, "hostname", workload, "simple_test")
            exp1_script = os.path.join(exp1_dir, "execute_experiment")
            assert not os.path.isfile(exp1_script)
