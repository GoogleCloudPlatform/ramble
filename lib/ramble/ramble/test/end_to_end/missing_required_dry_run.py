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
from ramble.main import RambleCommand, RambleCommandError


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_missing_required_dry_run(mutable_config, mutable_mock_workspace_path):
    """Tests tty.die at end of ramble.application_types.spack._create_software_env"""
    test_config = """
ramble:
  variants:
    package_manager: spack
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: 30
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    wrfv3:
      workloads:
        CONUS_2p5km:
          experiments:
            eight_node:
              variables:
                n_nodes: '8'
  software:
    packages:
      gcc8:
        pkg_spec: gcc@8.2.0 target=x86_64
        compiler_spec: gcc@8.2.0
      impi2018:
        pkg_spec: intel-mpi@2018.4.274 target=x86_64
        compiler: gcc8
      wrfv3:
        pkg_spec: my_wrf@3.9.1.1 build_type=dm+sm compile_type=em_real nesting=basic ~pnetcdf
        compiler: gcc8
    environments:
      wrfv3:
        packages:
        - impi2018
        - wrfv3
"""

    workspace_name = "test_missing_required_dry_run"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        with pytest.raises(RambleCommandError):
            captured = workspace("setup", "--dry-run", global_args=["-w", workspace_name])

            assert "Software spec wrf is not defined in environment wrfv3" in captured
