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
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    'mutable_config',
    'mutable_mock_workspace_path',
)

workspace = RambleCommand('workspace')


def test_spack_env_cache():
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
    processes_per_node: '1'
  applications:
    gromacs:
      workloads:
        water_bare:
          experiments:
            test1:
              variables:
                n_nodes: '1'
            test2:
              variables:
                n_nodes: '2'
                env_name: 'g2'
            test3:
              variables:
                n_nodes: '3'
        water_gmx50:
          experiments:
            test4:
              variables:
                n_nodes: '1'
  spack:
    packages:
      intel-mpi:
        spack_spec: intel-oneapi-mpi@2021.11.0
      gromacs:
        spack_spec: gromacs
    environments:
      gromacs:
        packages:
        - gromacs
        - intel-mpi
      g2:
        packages:
        - gromacs
        - intel-mpi
"""
    workspace_name = 'test-spack-env-cache'
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws._re_read()

    workspace(
        'setup',
        '--dry-run',
        global_args=['-w', workspace_name],
    )

    # spack env should be present only at the env_name level.
    assert os.path.exists(os.path.join(ws.software_dir, 'gromacs'))
    assert os.path.exists(os.path.join(ws.software_dir, 'g2'))
    assert not os.path.exists(os.path.join(ws.software_dir, 'g2.water_bare'))

    # First encounter of an env_name (test1 -> gromacs, test2 -> g2) requires spack usage.
    test1_log = os.path.join(ws.log_dir, 'setup.latest', 'gromacs.water_bare.test1.out')
    with open(test1_log, 'r') as f:
        content = f.read()
        assert 'spack install' in content
        assert 'spack concretize' in content

    test2_log = os.path.join(ws.log_dir, 'setup.latest', 'gromacs.water_bare.test2.out')
    with open(test2_log, 'r') as f:
        content = f.read()
        assert 'spack install' in content
        assert 'spack concretize' in content

    # Envs should already exist and can skip spack calls.
    test3_log = os.path.join(ws.log_dir, 'setup.latest', 'gromacs.water_bare.test3.out')
    with open(test3_log, 'r') as f:
        content = f.read()
        assert 'spack install' not in content
        assert 'spack concretize' not in content

    test4_log = os.path.join(
        ws.log_dir, 'setup.latest', 'gromacs.water_gmx50.test4.out'
    )
    with open(test4_log, 'r') as f:
        content = f.read()
        assert 'spack install' not in content
        assert 'spack concretize' not in content
