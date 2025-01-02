# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")


def test_experiment_modification(
    mutable_mock_workspace_path, mutable_applications, mock_modifiers, request
):
    workspace_name = request.node.name

    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks}'
    batch_submit: ''
    n_ranks: '{processes_per_node}*{n_nodes}'
    processes_per_node: '1'
  applications:
    gromacs:
      workloads:
        water_bare:
          experiments:
            'test-{n_ranks}':
              variables:
                n_nodes: [1, 2]
              modifiers:
              - name: modify-experiment
  spack:
    packages: {}
    environments: {}
"""

    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws1._re_read()

        workspace("concretize", global_args=["-D", ws1.root])
        workspace("setup", "--dry-run", global_args=["-D", ws1.root])

        n_ranks_vals = ["5", "10"]
        for n_ranks in n_ranks_vals:
            exp_script = os.path.join(
                ws1.experiment_dir,
                "gromacs",
                "water_bare",
                f"test-{n_ranks}",
                "execute_experiment",
            )

            assert os.path.exists(exp_script)

            with open(exp_script) as f:
                data = f.read()
                assert f"mpirun -n {n_ranks}" in data
