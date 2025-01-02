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
pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


def _spack_loc_log_line(pkg_spec):
    return f"with args: ['location', '-i', '{pkg_spec}']"


def test_define_package_paths():
    test_config = """
ramble:
  variants:
    package_manager: spack
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
  software:
    packages:
      gromacs:
        pkg_spec: gromacs
      intel-mpi:
        pkg_spec: intel-oneapi-mpi@2021.11.0
    environments:
      gromacs:
        packages:
        - gromacs
        - intel-mpi
"""
    workspace_name = "test-define-package-paths"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    workspace(
        "setup",
        "--dry-run",
        global_args=["-w", workspace_name],
    )

    # test1 should attempt to invoke `spack location -i` on dep packages.
    test1_log = os.path.join(ws.log_dir, "setup.latest", "gromacs.water_bare.test1.out")
    gromacs_log_line = _spack_loc_log_line("gromacs")
    impi_log_line = _spack_loc_log_line("intel-oneapi-mpi@2021.11.0")
    with open(test1_log) as f:
        content = f.read()
        assert "Executing phase define_package_paths" in content
        assert content.count(gromacs_log_line) == 1
        assert content.count(impi_log_line) == 1

    # test2 should use cached paths without invoking spack.
    test2_log = os.path.join(ws.log_dir, "setup.latest", "gromacs.water_bare.test2.out")
    with open(test2_log) as f:
        content = f.read()
        assert "Executing phase define_package_paths" in content
        assert gromacs_log_line not in content
        assert impi_log_line not in content


def test_package_path_variables():
    test_config = """
ramble:
  variants:
    package_manager: spack
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
                gromacs_path: '/test/path'
                n_nodes: '1'
            test2:
              variables:
                n_nodes: '2'
  software:
    packages:
      gromacs:
        pkg_spec: gromacs
      intel-mpi:
        pkg_spec: intel-oneapi-mpi@2021.11.0
    environments:
      gromacs:
        packages:
        - gromacs
        - intel-mpi
"""
    workspace_name = "test-define-package-paths"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    workspace(
        "setup",
        "--dry-run",
        global_args=["-w", workspace_name],
    )

    # test1 should attempt to invoke `spack location -i` on dep packages.
    # However this will not be cached in practice.
    test1_log = os.path.join(ws.log_dir, "setup.latest", "gromacs.water_bare.test1.out")
    gromacs_log_line = _spack_loc_log_line("gromacs")
    impi_log_line = _spack_loc_log_line("intel-oneapi-mpi@2021.11.0")
    with open(test1_log) as f:
        content = f.read()
        assert "Executing phase define_package_paths" in content
        assert content.count(gromacs_log_line) == 1
        assert content.count(impi_log_line) == 1

    # test2 should not use a path, as test1 has a variable for the path defined
    test2_log = os.path.join(ws.log_dir, "setup.latest", "gromacs.water_bare.test2.out")
    with open(test2_log) as f:
        content = f.read()
        assert "Executing phase define_package_paths" in content
        assert gromacs_log_line in content
        assert impi_log_line not in content
