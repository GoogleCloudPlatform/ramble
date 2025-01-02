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
from ramble.expander import RambleSyntaxError


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

config = ramble.main.RambleCommand("config")
workspace = RambleCommand("workspace")


def test_passthrough_variables(mutable_config, mutable_mock_workspace_path, mock_applications):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node} {undefined_var}'
    batch_submit: 'batch_submit {execute_experiment}'
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  env_vars:
    set:
      MY_VAR: TEST
  applications:
    basic:
      workloads:
        test_wl2:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_config_section_env_vars"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        experiment_root = ws.experiment_dir
        exp1_dir = os.path.join(experiment_root, "basic", "test_wl2", "simple_test")
        exp1_script = os.path.join(exp1_dir, "execute_experiment")

        import re

        undefined_regex = re.compile(r"{undefined_var}")

        # Assert undefined variable is found
        with open(exp1_script) as f:
            undefined_found = False
            for line in f.readlines():
                if undefined_regex.search(line):
                    undefined_found = True
            assert undefined_found


def test_disable_passthrough(mutable_config, mutable_mock_workspace_path):
    test_config = """
ramble:
  variables:
   batch_submit: '{execute_experiment}'
   processes_per_node: 1
  applications:
    hostname:
      workloads:
        parallel:
          experiments:
            test_exp:
              variables:
                mpi_command: '{undefined_var}'
                n_ranks: '1'
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_disable_passthrough"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        # Unexpanded variable should be allowed to passthrough without error
        captured = workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        assert "Encountered a passthrough error while expanding {mpi_command}" not in captured

        config("add", "config:disable_passthrough:true")

        with pytest.raises(RambleSyntaxError):
            captured = workspace("setup", "--dry-run", global_args=["-w", workspace_name])

            assert "Encountered a passthrough error while expanding {mpi_command}" in captured
