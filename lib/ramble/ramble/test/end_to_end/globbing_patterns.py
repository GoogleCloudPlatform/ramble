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


def test_globbing_patterns(
    mutable_config, mutable_mock_workspace_path, mock_applications, mock_modifiers
):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    glob-patterns:
      workloads:
        test_one_exec:
          experiments:
            test_no_wildcards_one_exec:
              variables:
                n_nodes: 1
        test_three_exec:
          experiments:
            test_wildcard_3_execs:
              variables:
                n_nodes: 1
              modifiers:
                - name: glob-patterns-mod
                  mode: test-glob
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_globbing_patterns"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        experiment_root = ws.experiment_dir
        exp1_dir = os.path.join(
            experiment_root, "glob-patterns", "test_one_exec", "test_no_wildcards_one_exec"
        )
        exp1_script = os.path.join(exp1_dir, "execute_experiment")
        exp2_dir = os.path.join(
            experiment_root, "glob-patterns", "test_three_exec", "test_wildcard_3_execs"
        )
        exp2_script = os.path.join(exp2_dir, "execute_experiment")

        import re

        test_cmd_regex = re.compile("base test .*>>")
        glob_cmd_regex = re.compile("test foo .*>>")
        baz_regex = re.compile("baz .*>>")

        test_wl_var_regex = re.compile("wl_var_test")
        glob_wl_var_regex = re.compile("wl_var_glob")
        baz_wl_var_regex = re.compile("wl_var_baz")

        test_env_var_regex = re.compile("env_var_test")
        glob_env_var_regex = re.compile("env_var_glob")
        baz_env_var_regex = re.compile("env_var_baz")

        glob_var_mod_regex = re.compile("var_mod_modified")
        glob_env_var_mod_regex = re.compile("env_var_mod=modded")

        with open(exp1_script) as f:
            # Check for only 'test' executable command
            test_cmd_found = False
            glob_cmd_not_found = True
            baz_cmd_not_found = True

            # Check for both test and glob workload vars
            test_wl_var_found = False
            glob_wl_var_found = False
            baz_wl_var_not_found = True

            # Check for both test and glob env vars
            test_env_var_found = False
            glob_env_var_found = False
            baz_env_var_not_found = True

            for line in f.readlines():
                # Executables
                if test_cmd_regex.search(line):
                    test_cmd_found = True
                if glob_cmd_regex.search(line):
                    glob_cmd_not_found = False
                if baz_regex.search(line):
                    baz_cmd_not_found = False

                # Workload vars
                if test_wl_var_regex.search(line):
                    test_wl_var_found = True
                if glob_wl_var_regex.search(line):
                    glob_wl_var_found = True
                if baz_wl_var_regex.search(line):
                    baz_wl_var_not_found = False

                # Env vars
                if test_env_var_regex.search(line):
                    test_env_var_found = True
                if glob_env_var_regex.search(line):
                    glob_env_var_found = True
                if baz_env_var_regex.search(line):
                    baz_env_var_not_found = False

            assert test_cmd_found and glob_cmd_not_found and baz_cmd_not_found
            assert test_wl_var_found and glob_wl_var_found and baz_wl_var_not_found
            assert test_env_var_found and glob_env_var_found and baz_env_var_not_found

        with open(exp2_script) as f:
            # Check for executables matching 'test*' glob pattern
            test_cmd_found = False
            glob_cmd_found = False
            baz_cmd_not_found = True

            # Check for only glob workload var
            test_wl_var_not_found = True
            glob_wl_var_found = False
            baz_wl_var_not_found = True

            # Check for only glob env var
            test_env_var_not_found = True
            glob_env_var_found = False
            baz_env_var_not_found = True

            # Check for modifier globbing
            glob_var_mod_found = False  # checks both variable modifier and modifier variable
            glob_env_var_mod_found = False

            for line in f.readlines():
                # Executables
                if test_cmd_regex.search(line):
                    test_cmd_found = True
                if glob_cmd_regex.search(line):
                    glob_cmd_found = True
                if baz_regex.search(line):
                    baz_cmd_not_found = False

                # Workload vars
                if test_wl_var_regex.search(line):
                    test_wl_var_not_found = False
                if glob_wl_var_regex.search(line):
                    glob_wl_var_found = True
                if baz_wl_var_regex.search(line):
                    baz_wl_var_not_found = False

                # Env vars
                if test_env_var_regex.search(line):
                    test_env_var_not_found = False
                if glob_env_var_regex.search(line):
                    glob_env_var_found = True
                if baz_env_var_regex.search(line):
                    baz_env_var_not_found = False

                # Modifier
                if glob_var_mod_regex.search(line):
                    glob_var_mod_found = True
                if glob_env_var_mod_regex.search(line):
                    glob_env_var_mod_found = True

            assert test_cmd_found and glob_cmd_found and baz_cmd_not_found
            assert test_wl_var_not_found and glob_wl_var_found and baz_wl_var_not_found
            assert test_env_var_not_found and glob_env_var_found and baz_env_var_not_found
            assert glob_var_mod_found and glob_env_var_mod_found
