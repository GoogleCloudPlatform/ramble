# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")
workspace = RambleCommand("workspace")


@pytest.mark.perf
@pytest.mark.long
def test_many_objects_defaults(make_workspace_from_config, ramble_benchmark):
    # This test is designed to stress the variable expansion and object creation
    # by using many modifiers, each with many default variables.
    # It aims to verify performance when a large number of objects are present.

    modifiers = [
        "nccl-env",
        "env-var-aggregator",
        "exit-code",
        "intel-aps",
        "install-ramble",
        "install-spack",
        "sys-stat",
        "nvidia-smi",
        "status-markers",
    ]

    modifier_list_yaml = "\n".join([f"    - name: {m}" for m in modifiers])
    modifier_section = f"  modifiers:\n{modifier_list_yaml}"

    # Create 200 experiments (10 x 20 matrix)
    # Each experiment has 9 modifiers.
    # Each experiment will have ~171 default variables.
    # Total variable objects = 200 * 171 = 34,200.

    matrix_var_list = ", ".join([f"'{i}'" for i in range(20)])

    test_config = f"""\
ramble:
  variants:
    package_manager: spack
    workflow_manager: slurm
  variables:
    mpi_command: ''
    batch_submit: '{{execute_experiment}}'
    processes_per_node: 1
{modifier_section}
  applications:
    hostname:
      workloads:
        local:
          experiments:
            exp_{{n_nodes}}_{{matrix_var}}:
              variables:
                n_nodes: [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
                matrix_var: [{matrix_var_list}]
              matrix:
              - n_nodes
              - matrix_var
"""
    ws, ws_name = make_workspace_from_config(test_config)

    # We only run setup --dry-run to trigger the expansion and object creation
    ramble_benchmark(workspace, "setup", "--dry-run", global_args=["-w", ws_name])

    # Verify that the correct number of experiments were created
    application_dir = os.path.join(ws.experiment_dir, "hostname", "local")
    experiments = [
        d for d in os.listdir(application_dir) if os.path.isdir(os.path.join(application_dir, d))
    ]
    assert len(experiments) == 200

    # Verify that at least one experiment was created
    exp_dir = os.path.join(ws.experiment_dir, "hostname", "local", "exp_1_0")
    assert os.path.isdir(exp_dir)

    # Verify that a middle experiment was created
    exp_dir = os.path.join(ws.experiment_dir, "hostname", "local", "exp_256_10")
    assert os.path.isdir(exp_dir)

    # Verify that the last experiment was created
    exp_dir = os.path.join(ws.experiment_dir, "hostname", "local", "exp_512_19")
    assert os.path.isdir(exp_dir)
