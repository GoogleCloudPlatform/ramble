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
from ramble.main import RambleCommand
from ramble.application import ApplicationError


pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_object_validation(mock_applications):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    partition: 'part1'
    processes_per_node: '1'
    n_threads: '1'
  applications:
    basic-inherited-noname:
      workloads:
        test_wl:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    ws_name = "test_object_validation"
    with ramble.workspace.create(ws_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()
        with pytest.raises(
            ApplicationError,
            match="Object class BasicInheritedNoname is missing required attribute 'name'",
        ):
            workspace("setup", "--dry-run", global_args=["-w", ws_name])
