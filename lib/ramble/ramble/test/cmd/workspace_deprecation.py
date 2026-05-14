# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import deprecation
import pytest

import ramble.workspace
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures("mutable_mock_workspace_path")


workspace = RambleCommand("workspace")


@deprecation.fail_if_not_removed
def test_manage_experiments_package_manager_deprecation(workspace_name):
    ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]
    workspace(
        "manage",
        "experiments",
        "hostname",
        "--wf",
        "local",
        "-p",
        "spack",
        global_args=global_args,
    )


@deprecation.fail_if_not_removed
def test_manage_experiments_workflow_manager_deprecation(workspace_name):
    ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]
    workspace(
        "manage",
        "experiments",
        "hostname",
        "--wf",
        "local",
        "--wm",
        "user-managed",
        global_args=global_args,
    )
