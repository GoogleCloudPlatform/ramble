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


def test_experiment_templates(mutable_config, mutable_mock_workspace_path):
    test_config = r"""
ramble:
  variables:
    processes_per_node: 16
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
    n_ranks: 1
  applications:
    hostname:
      workloads:
        serial:
          experiments:
            unused_template:
              template: True
            used_template:
              template: True
            template_false:
              template: False
            base_exp:
              chained_experiments:
              - name: 'hostname.serial.used_template'
                command: '{execute_experiment}'
                order: 'before_root'
              - name: 'hostname.serial.template_false'
                command: '{execute_experiment}'
                order: 'after_root'
"""
    workspace_name = "test_experiment_templates"
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws1._re_read()

        workspace("setup", global_args=["-w", workspace_name])

        expected_experiments = [
            "template_false",
            "base_exp",
        ]

        expected_chained_experiments = [
            "0.hostname.serial.used_template",
            "1.hostname.serial.template_false",
        ]

        unexpected_experiments = ["unused_template", "used_template"]

        for exp in unexpected_experiments:
            exp_dir = os.path.join(ws1.root, "experiments", "hostname", "serial", exp)
            assert not os.path.isdir(exp_dir)

        for exp in expected_experiments:
            exp_dir = os.path.join(ws1.root, "experiments", "hostname", "serial", exp)
            assert os.path.isdir(exp_dir)
            assert os.path.exists(os.path.join(exp_dir, "execute_experiment"))

        for exp in expected_chained_experiments:
            exp_dir = os.path.join(
                ws1.root,
                "experiments",
                "hostname",
                "serial",
                "base_exp",
                "chained_experiments",
                exp,
            )
            assert os.path.isdir(exp_dir)
            assert os.path.exists(os.path.join(exp_dir, "execute_experiment"))
