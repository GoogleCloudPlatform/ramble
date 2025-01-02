# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import glob
import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand
from ramble.test.dry_run_helpers import search_files_for_string

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


def assert_text_in_mirror_logs(ws, text):
    mirror_logs = glob.glob(os.path.join(ws.log_dir, "**", "*.out"))
    assert search_files_for_string(mirror_logs, text)


def test_warn_mirror_support(tmpdir):
    test_config = """
ramble:
  variants:
    package_manager: pip
  variables:
    mpi_command: ''
    batch_submit: '{execute_experiment}'
    processes_per_node: 1
    n_ranks: 1
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test: {}
  software:
    packages: {}
    environments: {}
"""
    ws_name = "test_pip_mirror_support"
    ws = ramble.workspace.create(ws_name)
    ramble.workspace.activate(ws)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    mirror_path = os.path.join(tmpdir, ws_name)
    workspace("mirror", "--dry-run", "-d", mirror_path)
    assert_text_in_mirror_logs(
        ws, "Warning: Mirroring software using pip is not currently supported"
    )
