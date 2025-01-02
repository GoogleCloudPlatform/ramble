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
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_expanded_foms_dry_run(mutable_config, mutable_mock_workspace_path, mock_applications):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    n_threads: '1'
  applications:
    expanded_foms:
      workloads:
        test_wl:
          experiments:
            single_exp:
              variables:
                n_nodes: 1
                n_ranks: 1
  software:
    packages: {}
    environments: {}
"""

    workspace_name = "test_end_to_end_expanded_foms"
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        # Write a command template
        with open(os.path.join(ws1.config_dir, "full_command.tpl"), "w+") as f:
            f.write("{command}")

        ws1._re_read()

        ws1.concretize()
        output = workspace("setup", "--dry-run", global_args=["-w", workspace_name])

        # Create fake figures of merit.
        expected_expansions = ["MPI", "test1", "123"]

        exp_dir = os.path.join(ws1.root, "experiments", "expanded_foms", "test_wl", "single_exp")
        fom_out_file = os.path.join(exp_dir, "single_exp.out")

        unit = "seconds"
        with open(fom_out_file, "w+") as f:
            for expected in expected_expansions:
                f.write(f"Collect FOM {expected} = 567.8 {unit}\n")

        ws1._re_read()
        output = workspace("analyze", global_args=["-w", workspace_name])
        print(output)

        text_results_files = glob.glob(os.path.join(ws1.root, "results*.txt"))
        with open(text_results_files[0]) as f:
            data = f.read()
            for expected in expected_expansions:
                assert f"test_fom {expected} = 567.8 {unit}" in data
