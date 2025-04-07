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
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config", "mutable_mock_workspace_path", "mutable_mock_apps_repo"
)

workspace = RambleCommand("workspace")


def test_object_import_separate_python_source(request):
    ws_name = request.node.name
    ws = ramble.workspace.create(ws_name)
    global_args = ["-w", ws_name]

    workspace(
        "manage",
        "experiments",
        "import-test",
        "-v",
        "n_nodes=1",
        "-v",
        "processes_per_node=1",
        global_args=global_args,
    )

    workspace("setup", global_args=global_args)

    rendered_script = os.path.join(
        ws.experiment_dir, "import-test", "test", "generated", "execute_experiment"
    )
    with open(rendered_script) as f:
        content = f.read()
        assert "echo 1" in content
