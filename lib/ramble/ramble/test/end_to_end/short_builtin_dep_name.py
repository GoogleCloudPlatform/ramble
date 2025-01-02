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
from ramble.main import RambleCommand
from ramble.graphs import GraphNodeAmbiguousError

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


def test_short_builtin_dep_name(mock_applications):
    test_config = """
ramble:
  variants:
    package_manager: spack
  variables:
    mpi_command: mpirun -n {n_ranks}
    batch_submit: '{execute_experiment}'
    processes_per_node: 1
    n_nodes: 1
  applications:
    test-builtin-dep-name:
      workloads:
        standard:
          experiments:
            test: {}
  software:
    packages: {}
    environments: {}
"""
    ws_name = "test_short_builtin_dep_name"
    ws = ramble.workspace.create(ws_name)
    ramble.workspace.activate(ws)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    with pytest.raises(GraphNodeAmbiguousError):
        workspace("setup", "--dry-run", global_args=["-w", ws_name])
