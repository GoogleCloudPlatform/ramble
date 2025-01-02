# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.application
import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand, RambleCommandError


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_unsetup_workspace_cannot_analyze(
    mutable_config, mutable_mock_workspace_path, mock_applications, capsys
):
    test_config = """
ramble:
  variants:
    package_manager: spack
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    zlib:
      workloads:
        ensure_installed:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
              env_vars:
                set:
                  MY_VAR: 'TEST'
  software:
    packages:
      zlib:
        pkg_spec: zlib
    environments:
      zlib:
        packages:
        - zlib
"""
    workspace_name = "test_unsetup_workspace_cannot_analyze"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        assert not os.path.exists(os.path.join(ws.experiment_dir, "zlib"))

        with pytest.raises(RambleCommandError):
            output = workspace("analyze", global_args=["-w", workspace_name])
            assert "Make sure your workspace is fully setup" in output
