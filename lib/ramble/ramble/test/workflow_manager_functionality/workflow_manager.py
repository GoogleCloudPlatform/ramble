# Copyright 2022-2026 The Ramble Authors
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


def test_default_workflow_manager_banner(workspace_name):
    test_config = """
ramble:
  variables:
    processes_per_node: 1
    n_nodes: 1
    mpi_command: ""
    batch_submit: ""
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test_default: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()
        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)
        with open(config_path, "w+", encoding="utf-8") as f:
            f.write(test_config)
        ws._re_read()
        workspace("setup", "--dry-run", global_args=["-D", ws.root])

        path = os.path.join(ws.experiment_dir, "hostname", "local", "test_default")
        with open(os.path.join(path, "execute_experiment"), encoding="utf-8") as f:
            content = f.read()
            assert "{workflow_banner}" not in content
            assert (
                "If this file is not the same as the above path, it is unlikely that this script"
                in content
            )


def test_workflow_manager_sbatch_warning(workspace_name):
    from unittest.mock import patch

    test_config = """
ramble:
  variants:
    workflow_manager: slurm
  variables:
    processes_per_node: 1
    n_nodes: 1
    mpi_command: ""
    batch_submit: ""
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test_default: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()
        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)
        with open(config_path, "w+", encoding="utf-8") as f:
            f.write(test_config)

        # Overwrite execute_experiment.tpl to contain #SBATCH
        tpl_path = os.path.join(ws.config_dir, "execute_experiment.tpl")
        with open(tpl_path, "w+", encoding="utf-8") as f:
            f.write("""{workflow_banner}
#SBATCH --custom-header
cd "{experiment_run_dir}"
{command}
""")

        ws._re_read()

        with patch("ramble.util.logger.logger.warn") as mock_warn:
            workspace("setup", "--dry-run", global_args=["-D", ws.root])
            # Assert logger.warn was called with the specific message
            assert mock_warn.called
            expected_msg = (
                "Validator 'check_sbatch_in_execute_experiment' (defined in 'slurm') "
                "fails with message: 'In experiment hostname.local.test_default:\n"
                "  `execute_experiment` contains `#SBATCH` directives, "
                "which will be ignored.\n"
                "  Custom headers should be added to `extra_sbatch_headers` "
                "in the workspace configuration instead.'"
            )
            mock_warn.assert_any_call(expected_msg)
