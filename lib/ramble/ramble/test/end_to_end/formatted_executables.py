# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.application import FormattedExecutableError
import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_formatted_executables(mutable_config, mutable_mock_workspace_path, mock_applications):
    test_config = r"""
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
    processes_per_node: '16'
    n_threads: '1'
  formatted_executables:
    ws_exec_def:
      prefix: 'from_ws '
      indentation: 9
      join_separator: ';'
    ws_test_def:
      prefix: 'test_from_ws '
      indentation: 2
      commands:
      - '{mpi_command} test'
  applications:
    basic:
      formatted_executables:
        app_exec_def:
          prefix: 'from_app '
      workloads:
        working_wl:
          formatted_executables:
            wl_exec_def:
              prefix: 'from_wl '
              indentation: 11
          experiments:
            simple_test:
              formatted_executables:
                exp_exec_def:
                  prefix: 'from_exp '
                  indentation: 10
                  join_separator: '\n'
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_formatted_executables"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        with open(os.path.join(ws.config_dir, "execute_experiment.tpl"), "w+") as f:
            f.write("{ws_exec_def}\n")
            f.write("{app_exec_def}\n")
            f.write("{wl_exec_def}\n")
            f.write("{exp_exec_def}\n")
            f.write("{ws_test_def}\n")
        ws._re_read()

        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        experiment_root = ws.experiment_dir
        exp_dir = os.path.join(experiment_root, "basic", "working_wl", "simple_test")
        exp_script = os.path.join(exp_dir, "execute_experiment")

        with open(exp_script) as f:
            data = f.read()
            assert "from_app echo" in data
            assert ";" + " " * 9 + "from_ws echo" in data
            assert "\n" + " " * 11 + "from_wl echo" in data
            assert "\n" + " " * 10 + "from_exp echo" in data
            assert "\n" + " " * 2 + "test_from_ws mpirun -n 16 -ppn 16 test" in data


def test_redefined_executable_errors(
    mutable_config, mutable_mock_workspace_path, mock_applications
):
    test_config = r"""
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    basic:
      workloads:
        working_wl:
          experiments:
            simple_test:
              formatted_executables:
                var_exec_name:
                  indentation: 3
                  join_separator: '\n'
              variables:
                var_exec_name: 'nothing'
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_redefined_executable_errors"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws._re_read()

        with pytest.raises(FormattedExecutableError):
            output = workspace("setup", "--dry-run", global_args=["-w", workspace_name])
            assert "Formatted executable var_exec_name defined" in output
