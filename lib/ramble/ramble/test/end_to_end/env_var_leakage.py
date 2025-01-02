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


def test_env_vars_do_not_leak(mutable_config, mutable_mock_workspace_path):
    test_config = """
ramble:
  config:
    shell: bash
  env_vars:
    set:
      CUDA_VISIBLE_DEVICES: 0,1,2,3,4,5,6,7
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    nvidia-hpl:
      workloads:
        calculator:
          experiments:
            test:
              variables:
                n_nodes: 1
    nccl-tests:
      workloads:
        all-reduce:
          experiments:
            test:
              variables:
                nccl-tests_path: /not/a/path
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_env_var_command"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        experiment_root = ws.experiment_dir
        exp1_dir = os.path.join(experiment_root, "nvidia-hpl", "calculator", "test")
        exp1_script = os.path.join(exp1_dir, "execute_experiment")
        exp2_dir = os.path.join(experiment_root, "nccl-tests", "all-reduce", "test")
        exp2_script = os.path.join(exp2_dir, "execute_experiment")

        with open(exp1_script) as f:
            content = f.read()
            assert "HPL_" in content

        with open(exp2_script) as f:
            content = f.read()
            assert "HPL_" not in content
