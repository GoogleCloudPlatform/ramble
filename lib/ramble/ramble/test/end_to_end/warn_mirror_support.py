# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import glob
import os

import pytest

from ramble.main import RambleCommand
from ramble.test.dry_run_helpers import search_files_for_string

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "workspace_deactivate",
)

workspace = RambleCommand("workspace")


def assert_text_in_mirror_logs(ws, text):
    mirror_logs = glob.glob(os.path.join(ws.log_dir, "**", "*.out"))
    assert search_files_for_string(mirror_logs, text)


def test_warn_mirror_support(tmpdir, make_workspace_from_config):
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
    ws, ws_name = make_workspace_from_config(test_config, name=ws_name, activate=True)

    mirror_path = os.path.join(tmpdir, ws_name)
    workspace("mirror", "--dry-run", "-d", mirror_path)
    assert_text_in_mirror_logs(
        ws, "Warning: Mirroring software using pip is not currently supported"
    )
