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


def test_env_var_builtin(mutable_config, mutable_mock_workspace_path, mock_applications):
    test_config = """
ramble:
  config:
    shell: bash
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    interleved-env-vars:
      workloads:
        test_wl:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
              env_vars:
                set:
                  MY_VAR: 'TEST'
        test_wl2:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
              env_vars:
                set:
                  MY_VAR: 'TEST'
        test_wl3:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
              env_vars:
                set:
                  MY_VAR: 'TEST'
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
        exp1_dir = os.path.join(experiment_root, "interleved-env-vars", "test_wl", "simple_test")
        exp1_script = os.path.join(exp1_dir, "execute_experiment")
        exp2_dir = os.path.join(experiment_root, "interleved-env-vars", "test_wl2", "simple_test")
        exp2_script = os.path.join(exp2_dir, "execute_experiment")
        exp3_dir = os.path.join(experiment_root, "interleved-env-vars", "test_wl3", "simple_test")
        exp3_script = os.path.join(exp3_dir, "execute_experiment")

        import re

        export_regex = re.compile(r"export MY_VAR=TEST")
        cmd1_regex = re.compile("bar >>")
        cmd2_regex = re.compile("baz >>")
        cmd3_regex = re.compile("foo >>")

        # Assert experiment 1 has exports before commands
        with open(exp1_script) as f:
            cmd_found = False
            export_found = False
            for line in f.readlines():
                if not export_found and export_regex.search(line):
                    assert not cmd_found
                    export_found = True
                if export_found and cmd1_regex.search(line):
                    cmd_found = True
            assert cmd_found and export_found

        # Assert experiment 2 has commands before exports
        with open(exp2_script) as f:
            cmd_found = False
            export_found = False
            for line in f.readlines():
                if not cmd_found and cmd2_regex.search(line):
                    assert not export_found
                    cmd_found = True
                if cmd_found and export_regex.search(line):
                    export_found = True
            assert cmd_found and export_found

        # Assert experiment 3 has exports before commands
        with open(exp3_script) as f:
            cmd_found = False
            export_found = False
            for line in f.readlines():
                if not export_found and export_regex.search(line):
                    assert not cmd_found
                    export_found = True
                if export_found and cmd3_regex.search(line):
                    cmd_found = True
            assert cmd_found and export_found


def test_env_var_from_app_only(mutable_config, mutable_mock_workspace_path, mock_applications):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    interleved-env-vars:
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
    workspace_name = "test_env_var_from_app_only"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        experiment_root = ws.experiment_dir
        exp1_dir = os.path.join(experiment_root, "interleved-env-vars", "test_wl", "simple_test")

        with open(os.path.join(exp1_dir, "execute_experiment")) as f:
            assert "FROM_DIRECTIVE" in f.read()
