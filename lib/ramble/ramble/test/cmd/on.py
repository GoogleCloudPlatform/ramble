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
import ramble.test.cmd.workspace
import ramble.pipeline
import ramble.filters
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config", "mutable_mock_workspace_path", "mutable_mock_apps_repo"
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
