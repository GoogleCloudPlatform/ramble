# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_gromacs_size_expansion(make_workspace):
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
        pkg_spec: intel-oneapi-mpi@2021.13.1
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

    ws, ws_name = make_workspace(test_config)

    workspace("setup", "--dry-run", global_args=["-w", ws_name])

    exec_script_path = os.path.join(
        ws.experiment_dir, "gromacs", "water_bare", "expansion_test", "execute_experiment"
    )

    with open(exec_script_path) as f:
        assert "0000.96" in f.read()
