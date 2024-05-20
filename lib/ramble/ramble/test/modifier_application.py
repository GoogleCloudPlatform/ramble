# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace

from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path')

workspace = RambleCommand('workspace')


def test_wrfv4_aps_test(mutable_config, mutable_mock_workspace_path):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '10'
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    wrfv4:
      workloads:
        CONUS_12km:
          experiments:
            modifier_test:
              modifiers:
              - name: intel-aps
                mode: mpi
                on_executable:
                - '*'
              variables:
                n_nodes: '1'
  spack:
    packages:
      gcc:
        spack_spec: gcc@8.5.0
      intel-mpi:
        spack_spec: intel-mpi@2018.4.274
        compiler: gcc
      wrfv4:
        spack_spec: wrf@4.2 build_type=dm+sm compile_type=em_real nesting=basic ~chem ~pnetcdf
        compiler: gcc
      intel-oneapi-vtune:
        spack_spec: intel-oneapi-vtune
    environments:
      wrfv4:
        packages:
        - wrfv4
        - intel-mpi
        - intel-oneapi-vtune
"""

    workspace_name = 'test_wrfv4_modified_aps'
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)

        ws1._re_read()

        workspace('setup', '--dry-run', global_args=['-w', workspace_name])

        software_path = os.path.join(ws1.software_dir, 'wrfv4', 'spack.yaml')
        with open(software_path, 'r') as f:
            assert 'intel-oneapi-vtune' in f.read()

        execute_script = os.path.join(ws1.experiment_dir, 'wrfv4', 'CONUS_12km',
                                      'modifier_test', 'execute_experiment')
        with open(execute_script, 'r') as f:
            data = f.read()
            assert 'aps -c mpi' in data
            assert 'aps-report' in data
