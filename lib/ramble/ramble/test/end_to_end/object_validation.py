# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.config
import ramble.workspace
from ramble import application
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config", "mutable_mock_workspace_path", "mock_applications"
)

workspace = RambleCommand("workspace")


def test_object_validation(workspace_name):
    global_args = ["-w", workspace_name]

    ws = ramble.workspace.create(workspace_name)
    workspace(
        "manage",
        "experiments",
        "validation",
        "-v",
        "n_nodes=3",
        "-v",
        "processes_per_node=1",
        "-v",
        "batch_submit={execute_experiment}",
        global_args=global_args,
    )
    ws._re_read()
    with pytest.raises(
        application.ObjectValidationError, match="should run with even number of processes"
    ):
        workspace("setup", global_args=global_args)

    # Correct configuration should pass
    workspace(
        "manage",
        "experiments",
        "validation",
        "-v",
        "n_nodes=2",
        "-v",
        "processes_per_node=1",
        "--overwrite",
        global_args=global_args,
    )
    ws._re_read()
    out = workspace("setup", global_args=global_args)
    assert "Warning:" not in out

    # Validator without fail_on_invalid should only issue a warning
    workspace(
        "manage",
        "experiments",
        "validation",
        "-v",
        "validate_var=invalid",
        "-v",
        "n_nodes=2",
        "-v",
        "processes_per_node=1",
        "--overwrite",
        global_args=global_args,
    )
    ws._re_read()

    out = workspace("setup", global_args=global_args)
    assert "Warning: Validator 'validate_var_check'" in out
    assert "The validate_var is recommended to start with 'valid', but got 'invalid'" in out
