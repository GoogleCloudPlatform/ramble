# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.filters
import ramble.pipeline
import ramble.test.cmd.workspace
import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "mutable_mock_apps_repo",
    "workspace_deactivate",
)

workspace = RambleCommand("workspace")
on = RambleCommand("on")


def test_on_command():
    ws_name = "test"
    workspace("create", ws_name)
    assert ws_name in workspace("list")

    with ramble.workspace.read("test") as ws:
        ramble.test.cmd.workspace.add_basic(ws)
        ramble.test.cmd.workspace.check_basic(ws)

        workspace("setup")
        assert os.path.exists(ws.root + "/all_experiments")

        on(global_args=["-w", ws_name])


def test_execute_pipeline():
    ws_name = "test"
    workspace("create", ws_name)
    assert ws_name in workspace("list")

    setup_pipeline_type = ramble.pipeline.pipelines.setup
    setup_pipeline_class = ramble.pipeline.pipeline_class(setup_pipeline_type)
    execute_pipeline_type = ramble.pipeline.pipelines.execute
    execute_pipeline_class = ramble.pipeline.pipeline_class(execute_pipeline_type)
    filters = ramble.filters.Filters()

    with ramble.workspace.read(ws_name) as ws:
        ramble.test.cmd.workspace.add_basic(ws)
        ramble.test.cmd.workspace.check_basic(ws)

        setup_pipeline = setup_pipeline_class(ws, filters)
        setup_pipeline.run()
        assert os.path.exists(ws.root + "/all_experiments")

        execute_pipeline = execute_pipeline_class(ws, filters)
        execute_pipeline.run()


def test_on_where():
    ws_name = "test"
    workspace("create", ws_name)

    with ramble.workspace.read("test") as ws:
        ramble.test.cmd.workspace.add_basic(ws)
        ramble.test.cmd.workspace.check_basic(ws)

        workspace("setup")
        assert os.path.exists(ws.root + "/all_experiments")

        on("--where", '"{experiment_index}" == "1"', global_args=["-w", ws_name])


def test_on_executor():
    ws_name = "test"
    workspace("create", ws_name)

    with ramble.workspace.read("test") as ws:
        ramble.test.cmd.workspace.add_basic(ws)
        ramble.test.cmd.workspace.check_basic(ws)

        workspace("setup")
        assert os.path.exists(ws.root + "/all_experiments")

        on("--executor", 'echo "Index = {experiment_index}"', global_args=["-w", ws_name])


def test_on_executor_in_run_dir(workspace_name):
    global_args = ["-w", workspace_name]
    ws = ramble.workspace.create(workspace_name)
    workspace(
        "manage",
        "experiments",
        "basic",
        "--wf",
        "working_wl",
        "-v",
        "n_nodes=1",
        "-v",
        "processes_per_node=1",
        "-v",
        "batch_submit={execute_experiment}",
        "-v",
        "my_var=10",
        "--default-variable-value",
        "1",
        global_args=global_args,
    )

    # Assert executor not found
    with pytest.raises(Exception, match="my_exit: No such file or directory"):
        on("--executor", "my_exit", global_args=global_args)

    # Now set up the executor template
    tpl_path = os.path.join(ws.config_dir, "my_exit.tpl")
    with open(tpl_path, "w") as f:
        f.write("#!/bin/bash\n\nexit {my_var}")
    ws._re_read()
    workspace("setup", global_args=global_args)

    # Assert no executable permission against the template
    with pytest.raises(Exception, match="my_exit.tpl: Permission denied"):
        on("--executor", tpl_path, global_args=global_args)

    # Assert the executable is invoked
    with pytest.raises(Exception, match="Command exited with status 10"):
        on("--executor", "my_exit", global_args=global_args)
