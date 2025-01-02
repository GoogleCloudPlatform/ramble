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
config = RambleCommand("config")


def test_merge_config_files(mutable_config, mutable_mock_workspace_path, mock_applications):
    test_applications = """
applications:
  zlib:
    workloads:
      ensure_installed:
        experiments:
          test_experiment:
            variables:
              n_ranks: '1'
"""

    test_software = """
software:
  packages:
    zlib:
      pkg_spec: zlib@1.2.12
  environments:
    zlib:
      packages:
      - zlib
"""
    test_config = """
ramble:
  variants:
    package_manager: spack
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '16'
    n_threads: '1'
  applications: {}
  software:
    packages: {}
    environments: {}
"""
    test_licenses = """
licenses:
  zlib:
    set:
      TEST_LICENSE: 'port@server'
"""
    workspace_name = "test_merge_config_files"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws._re_read()

        applications_file = os.path.join(ws.root, "applications_test.yaml")
        software_file = os.path.join(ws.root, "software_test.yaml")
        licenses_file = os.path.join(ws.root, "licenses.yaml")

        with open(applications_file, "w+") as f:
            f.write(test_applications)

        with open(software_file, "w+") as f:
            f.write(test_software)

        with open(licenses_file, "w") as f:
            f.write(test_licenses)

        config("add", "-f", applications_file, global_args=["-w", workspace_name])
        config("add", "-f", software_file, global_args=["-w", workspace_name])
        config("add", "-f", licenses_file, global_args=["-w", workspace_name])

        ws._re_read()

        with open(config_path) as f:
            data = f.read()

            assert "ensure_installed" in data
            assert "test_experiment" in data
            assert "zlib" in data
            assert "pkg_spec: zlib@1.2.12" in data
            assert "licenses" in data
            assert "TEST_LICENSE: port@server" in data

        workspace("setup", "--dry-run", global_args=["-w", workspace_name])
        exec_file = os.path.join(
            ws.experiment_dir, "zlib", "ensure_installed", "test_experiment", "execute_experiment"
        )
        with open(exec_file) as f:
            assert "license.inc" in f.read()
