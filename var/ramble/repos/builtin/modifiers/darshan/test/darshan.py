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

workspace = RambleCommand("workspace")

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)


def test_darshan(request):
    ws_name = request.node.name
    test_config = """
ramble:
  modifiers:
  - name: darshan
  variables:
    processes_per_node: 1
    n_nodes: 2
    mpi_command: 'mpirun -n {n_rank}'
    batch_submit: '{execute_experiment}'
    darshan-runtime_path: 'fake-darshan-rt'
    darshan-util_path: 'fake-darshan-util'
  applications:
    hostname:
      workloads:
        parallel:
          experiments:
            test-impi:
              variables:
                intel-oneapi-mpi_path: 'fake-impi-path'
                darshan_log_path: 'darshan-log-dir'
            test-ompi:
              variables:
                openmpi_path: 'fake-ompi-path'
"""
    ws = ramble.workspace.create(ws_name)
    ws.write()
    config_path = os.path.join(
        ws.config_dir, ramble.workspace.config_file_name
    )
    with open(config_path, "w+") as f:
        f.write(test_config)
    ws._re_read()
    workspace("setup", "--dry-run", global_args=["-D", ws.root])
    run_dir = os.path.join(
        ws.experiment_dir, "hostname", "parallel", "test-impi"
    )
    with open(os.path.join(run_dir, "execute_experiment")) as f:
        content = f.read()
        assert 'export DARSHAN_LOG_DIR_PATH="darshan-log-dir"' in content
        assert (
            '_EXTRA_DARSHAN_MOD_MPI_COMMAND="-genv LD_PRELOAD fake-darshan-rt/lib/libdarshan.so"'
            in content
        )
        assert "unset _EXTRA_DARSHAN_MOD_MPI_COMMAND" in content
        assert "unset DARSHAN_LOG_DIR_PATH" in content
        assert "darshan-parser" in content
    run_dir2 = os.path.join(
        ws.experiment_dir, "hostname", "parallel", "test-ompi"
    )
    with open(os.path.join(run_dir2, "execute_experiment")) as f:
        content = f.read()
        assert (
            '_EXTRA_DARSHAN_MOD_MPI_COMMAND="-x LD_PRELOAD fake-darshan-rt/lib/libdarshan.so"'
            in content
        )
