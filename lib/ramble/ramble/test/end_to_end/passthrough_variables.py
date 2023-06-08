# Copyright 2022-2023 Google LLC
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
pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path')

workspace = RambleCommand('workspace')


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
  spack:
    concretized: true
    packages: {}
    environments: {}
"""
    workspace_name = 'test_config_section_env_vars'
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)
        ws._re_read()

        workspace('setup', '--dry-run', global_args=['-w', workspace_name])

        experiment_root = ws.experiment_dir
        exp1_dir = os.path.join(experiment_root, 'basic', 'test_wl2', 'simple_test')
        exp1_script = os.path.join(exp1_dir, 'execute_experiment')

        import re
        undefined_regex = re.compile(r'{undefined_var}')

        # Assert undefined variable is found
        with open(exp1_script, 'r') as f:
            undefined_found = False
            for line in f.readlines():
                if undefined_regex.search(line):
                    undefined_found = True
            assert undefined_found
