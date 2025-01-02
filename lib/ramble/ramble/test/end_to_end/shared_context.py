# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import glob

import pytest

import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "mock_applications",
    "mock_modifiers",
)

workspace = RambleCommand("workspace")


def test_shared_contexts(
    mutable_config, mutable_mock_workspace_path, mock_applications, mock_modifiers
):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    partition: 'part1'
    processes_per_node: '1'
    n_threads: '1'
  applications:
    shared-context:
      workloads:
        test_wl:
          experiments:
            simple_test:
              modifiers:
                - name: test-mod
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    workspace_name = "test_shared_context"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        # Create fake figures of merit.
        exp_dir = os.path.join(ws.root, "experiments", "shared-context", "test_wl", "simple_test")
        with open(os.path.join(exp_dir, "simple_test.out"), "w+") as f:
            f.write("fom_context mod_context\n")
            f.write("123.4 seconds app_fom\n")

        with open(os.path.join(exp_dir, "test_analysis.log"), "w+") as f:
            f.write("fom_contextFOM_GOES_HERE")

        workspace("analyze", "-f", "text", "json", global_args=["-w", workspace_name])

        results_files = glob.glob(os.path.join(ws.root, "results.latest.txt"))

        with open(results_files[0]) as f:
            data = f.read()
            assert "matched_shared_context" in data  # find the merged context
            assert "test_fom = 123.4" in data  # from the app
            assert "shared_context_fom" in data  # from the mod
