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


def test_custom_executables(mutable_config, mutable_mock_workspace_path, mock_applications):
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
        test_wl3:
          experiments:
            simple_test:
              internals:
                custom_executables:
                  lscpu:
                    template:
                    - 'lscpu'
                    use_mpi: false
                    redirect: '{log_file}'
                    output_capture: '>>'
                    run_in_background: true
                  before_all:
                    template:
                    - 'echo "before all"'
                  after_all:
                    template:
                    - 'echo "after all"'
                  before_env_vars:
                    template:
                    - 'echo "before env_vars {env_var_name}"'
                    variables:
                      env_var_name: 'OTHER_ENV_VAR'
                  after_env_vars:
                    template:
                    - 'echo "after env_vars {env_var_name}"'
                executables:
                - lscpu
                - builtin::env_vars
                - baz
                executable_injection:
                - name: before_all
                - name: after_all
                  order: after
                - name: before_env_vars
                  order: before
                  relative_to: builtin::env_vars
                - name: after_env_vars
                  order: after
                  relative_to: builtin::env_vars
              variables:
                n_nodes: 1
                env_var_name: 'MY_VAR'
              env_vars:
                set:
                  MY_VAR: 'TEST'
                  OTHER_ENV_VAR: 'ANOTHER_TEST'
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_custom_executables"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        experiment_root = ws.experiment_dir
        exp_dir = os.path.join(experiment_root, "interleved-env-vars", "test_wl3", "simple_test")
        exp_script = os.path.join(exp_dir, "execute_experiment")

        import re

        custom_regex = re.compile(r"^lscpu >> .* &$")
        export_regex = re.compile(r"export MY_VAR=TEST")
        cmd_regex = re.compile("foo >>")

        inject_order_regex = [
            re.compile('echo "before all"'),
            re.compile('echo "before env_vars OTHER_ENV_VAR"'),
            re.compile('echo "after env_vars MY_VAR"'),
            re.compile('echo "after all"'),
        ]

        # Assert command order is: lscpu -> export -> foo
        with open(exp_script) as f:
            custom_found = False
            cmd_found = False
            export_found = False

            inject_order_found = [
                False,
                False,
                False,
                False,
            ]
            inject_idx = 0

            for line in f.readlines():
                if not custom_found and custom_regex.search(line):
                    assert not cmd_found
                    assert not export_found
                    custom_found = True
                if custom_found and not export_found and export_regex.search(line):
                    assert not cmd_found
                    export_found = True
                if export_found and not cmd_found and cmd_regex.search(line):
                    cmd_found = True

                if inject_idx < len(inject_order_found):
                    if inject_order_regex[inject_idx].search(line):
                        inject_order_found[inject_idx] = True
                        inject_idx += 1

            assert custom_found and cmd_found and export_found
            assert all(inject_order_found)
