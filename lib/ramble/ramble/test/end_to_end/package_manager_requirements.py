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

from ramble.util.command_runner import RunnerError
from ramble.pkg_man.builtin.spack_lightweight import (
    SpackRunner,
    ValidationFailedError,
)


pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


@pytest.mark.long
def test_package_manager_requirements_zlib(mock_applications, mock_modifiers):
    test_config = """
ramble:
  variants:
    package_manager: spack
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '1'
    n_ranks: '1'
  modifiers:
  - name: spack-mod
  applications:
    zlib-configs:
      workloads:
        ensure_installed:
          experiments:
            test:
              variables: {}
  software:
    packages: {}
    environments:
      zlib-configs:
        packages: []
"""

    try:
        SpackRunner()
    except RunnerError as e:
        pytest.skip(e)

    workspace_name = "test_package_manager_requirements_zlib"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", global_args=["-w", workspace_name])

        spack_yaml = os.path.join(ws.software_dir, "spack", "zlib-configs", "spack.yaml")

        assert os.path.isfile(spack_yaml)

        with open(spack_yaml) as f:
            data = f.read()
            assert "config:" in data
            assert "debug: true" in data


def test_package_manager_requirements_error(mock_applications, mock_modifiers):
    test_config = """
ramble:
  variants:
    package_manager: spack
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '1'
    n_ranks: '1'
  modifiers:
  - name: spack-failed-reqs
  applications:
    zlib-configs:
      workloads:
        ensure_installed:
          experiments:
            test:
              variables: {}
  software:
    packages: {}
    environments:
      zlib-configs:
        packages: []
"""

    try:
        SpackRunner()
    except RunnerError as e:
        pytest.skip(e)

    workspace_name = "test_package_manager_requirements_error"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        with pytest.raises(ValidationFailedError) as e:
            workspace("setup", global_args=["-w", workspace_name])

            assert 'Validation of: "spack list not-a-package" failed' in e
