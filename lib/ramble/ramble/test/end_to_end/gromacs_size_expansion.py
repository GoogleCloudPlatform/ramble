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


def test_gromacs_size_expansion(mutable_config, mutable_mock_workspace_path):
    test_config = """
ramble:
  variants:
    package_manager: spack
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '1'
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    gromacs:
      workloads:
        water_bare:
          experiments:
            expansion_test:
              variables:
                n_nodes: '1'
                size: '0000.96'
  software:
    packages:
      gcc:
        pkg_spec: gcc@8.5.0
      intel-mpi:
        pkg_spec: intel-mpi@2018.4.274
        compiler: gcc
      gromacs:
        pkg_spec: gromacs
        compiler: gcc
    environments:
      gromacs:
        packages:
        - gromacs
        - intel-mpi
"""

    workspace_name = "test_gromacs_size_expansion"
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws1._re_read()

        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        exec_script_path = os.path.join(
            ws1.experiment_dir, "gromacs", "water_bare", "expansion_test", "execute_experiment"
        )

        with open(exec_script_path) as f:
            assert "0000.96" in f.read()
