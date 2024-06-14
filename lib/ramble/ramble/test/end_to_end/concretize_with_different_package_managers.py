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
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_concretize_with_different_package_managers(
    mutable_config, mutable_mock_workspace_path, request
):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
    processes_per_node: '1'
    n_ranks: '1'
    n_threads: '1'
  applications:
    wrfv4:
      variants:
        package_manager: 'spack-lightweight'
      workloads:
        CONUS_12km:
          experiments:
            test:
              variables:
                n_nodes: '1'
    gromacs:
      variants:
        package_manager: None
      workloads:
        water_bare:
          experiments:
            test:
              variables:
                n_nodes: '1'
  software:
    packages: {}
    environments: {}
"""

    workspace_name = request.node.name
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws1._re_read()

        workspace("concretize", global_args=["-w", workspace_name])

        sw_dict = ws1.get_software_dict()

        assert "wrfv4" in sw_dict["environments"]
        assert "wrfv4" in sw_dict["packages"]
        assert "gromacs" not in sw_dict["environments"]
        assert "gromacs" not in sw_dict["packages"]
