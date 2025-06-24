# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import re

import pytest

import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

config = RambleCommand("config")
workspace = RambleCommand("workspace")


def test_env_var_builtin(mock_applications, workspace_name):
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


def test_env_var_from_app_only(mock_applications, workspace_name):
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


def test_object_env_var_order(
    workspace_name,
    mutable_mock_apps_repo,
    mutable_mock_mods_repo,
    mutable_mock_pkg_mans_repo,
    mutable_mock_wms_repo,
):
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-directives",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "when-package-manager",
            "--wm",
            "when-workflow-manager",
            global_args=global_args,
        )

        mod_config_path = os.path.join(ws.config_dir, "modifiers.yaml")
        with open(mod_config_path, "w+") as f:
            f.write("modifiers:\n")
            f.write(" - name: when-modifier\n")

        config("add", "variants:app_env_var_included:true", global_args=global_args)
        config("add", "variants:workflow_manager_included:true", global_args=global_args)
        config("add", "variants:workflow_manager_env_var_included:true", global_args=global_args)
        config("add", "variants:package_manager_included:true", global_args=global_args)
        config("add", "variants:package_manager_env_var_included:true", global_args=global_args)
        config("add", "variants:mod_env_var_included:true", global_args=global_args)

        ws._re_read()
        workspace("setup", "--dry-run", global_args=global_args)

        regex_order = [
            re.compile(r"export APP_ENV_VAR=APP_ENV_VAR_SET;"),
            re.compile(r"export PACKAGE_ENV_VAR=PKG_ENV_VAR_SET;"),
            re.compile(r"export WORKFLOW_ENV_VAR=WF_ENV_VAR_SET;"),
            re.compile(r"export MOD_ENV_VAR=MOD_ENV_VAR_SET;"),
        ]

        found_order = [False for _ in regex_order]

        found_idx = 0

        rendered_script = os.path.join(
            ws.experiment_dir, "when-directives", "test_wl", "generated", "execute_experiment"
        )

        with open(rendered_script) as f:
            for line in f.readlines():
                cur_regex = regex_order[found_idx]
                if cur_regex.search(line):
                    found_order[found_idx] = True
                    found_idx += 1

                if found_idx == len(found_order):
                    break

        assert all(found_order)
