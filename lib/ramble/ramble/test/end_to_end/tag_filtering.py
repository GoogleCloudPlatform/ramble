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
on = RambleCommand("on")


def check_output(output, compared_list, contains=False):
    for item in compared_list:
        if contains:
            assert item in output
        else:
            assert item not in output


@pytest.mark.parametrize(
    "tag,expected_experiments,unexpected_experiments",
    [
        (
            "first",
            ["workload-tags.test_wl.first_experiment"],
            ["workload-tags.test_wl2.second_experiment"],
        )
    ],
)
def test_workspace_tag_filtering(
    mutable_config,
    mutable_mock_workspace_path,
    mock_applications,
    tag,
    expected_experiments,
    unexpected_experiments,
):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
    processes_per_node: 1
    n_threads: '1'
  applications:
    workload-tags:
      workloads:
        test_wl:
          experiments:
            first_experiment:
              tags:
              - first
              variables:
                n_nodes: 1
        test_wl2:
          experiments:
            second_experiment:
              tags:
              - second
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""

    workspace_name = f"test_tag_filtering_{tag}"
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws1._re_read()

        output = workspace("info", "--filter-tags", tag, global_args=["-w", workspace_name])

        check_output(output, expected_experiments, contains=True)
        check_output(output, unexpected_experiments, contains=False)

        output = workspace("setup", "--filter-tags", tag, global_args=["-v", "-w", workspace_name])

        check_output(output, expected_experiments, contains=True)
        check_output(output, unexpected_experiments, contains=False)

        output = on("--filter-tags", tag, global_args=["-v", "-w", workspace_name])

        output = workspace(
            "analyze", "--filter-tags", tag, global_args=["-v", "-w", workspace_name]
        )

        check_output(output, expected_experiments, contains=True)
        check_output(output, unexpected_experiments, contains=False)
