# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import llnl.util.filesystem as fs

import ramble.workspace
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config", "mutable_mock_workspace_path", "mutable_mock_apps_repo"
)

workspace = RambleCommand("workspace")


def test_nested_config_templates(workspace_name):
    test_config = """
ramble:
  variables:
    mpi_command: mpirun -n {n_ranks}
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: 1
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test:
              variables:
                n_nodes: 1
"""
    ws = ramble.workspace.create(workspace_name)
    ws.write()
    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)
    with open(config_path, "w+") as f:
        f.write(test_config)
    new_template_path = os.path.join(ws.config_dir, "templates", "test_template.tpl")
    fs.mkdirp(os.path.dirname(new_template_path))
    with open(new_template_path, "w+") as f:
        f.write("{templates/test_template}")
    ws._re_read()

    workspace("setup", "--dry-run", global_args=["-w", workspace_name])
    run_dir = os.path.join(ws.experiment_dir, "basic/test_wl/test/")
    script_path = os.path.join(run_dir, "templates", "test_template")
    assert os.path.isfile(script_path)
    with open(script_path) as f:
        data = f.read()
        assert "basic/test_wl/test/templates/test_template" in data

    # Test template archival
    workspace("archive", global_args=["-w", workspace_name])
    exp_archive_path = os.path.join(
        ws.latest_archive_path, "experiments", "basic", "test_wl", "test"
    )
    files = os.listdir(exp_archive_path)
    assert "test_template" in files
