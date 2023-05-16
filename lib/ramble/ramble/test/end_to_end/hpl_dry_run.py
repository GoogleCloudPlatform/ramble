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


def test_hpl_dry_run(mutable_config, mutable_mock_workspace_path):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: 16
    n_threads: 1
  applications:
    hpl:
      workloads:
        standard:
          experiments:
            test_exp:
              variables:
                n_ranks: 4
  spack:
    concretized: true
    packages:
      gcc9:
        spack_spec: gcc@9.3.0
      impi2018:
        spack_spec: intel-mpi@2018.4.274
        compiler: gcc9
      hpl:
        spack_spec: hpl@2.3 +openmp
        compiler: gcc9
    environments:
      hpl:
        packages:
        - hpl
        - impi2018
"""

    workspace_name = 'test_end_to_end_hpl'
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)

        # Write a command template
        with open(os.path.join(ws1.config_dir, 'full_command.tpl'), 'w+') as f:
            f.write('{command}')

        ws1._re_read()

        workspace('setup', '--dry-run', global_args=['-w', workspace_name])

        # Test software directories
        software_dirs = ['hpl.standard']
        software_base_dir = os.path.join(ws1.root, ramble.workspace.workspace_software_path)
        assert os.path.exists(software_base_dir)
        for software_dir in software_dirs:
            software_path = os.path.join(software_base_dir, software_dir)
            assert os.path.exists(software_path)

            spack_file = os.path.join(software_path, 'spack.yaml')
            assert os.path.exists(spack_file)

        expected_experiments = ['test_exp']

        for exp in expected_experiments:
            exp_dir = os.path.join(ws1.root, 'experiments',
                                   'hpl', 'standard', exp)
            assert os.path.isdir(exp_dir)
            assert os.path.exists(os.path.join(exp_dir, 'execute_experiment'))
