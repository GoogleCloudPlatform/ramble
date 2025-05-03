# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures("mutable_mock_workspace_path", "mutable_mock_apps_repo")

config = RambleCommand("config")
workspace = RambleCommand("workspace")


def test_register_phase_when(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-directives",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            global_args=global_args,
        )

        config("add", "variants:register_phase_when:true", global_args=global_args)

        ws._re_read()
        output = workspace("setup", "--dry-run", global_args=global_args)

        assert "Test Phase" in output

        config("remove", "variants:register_phase_when:true", global_args=global_args)
        config("add", "variants:register_phase_when:false", global_args=global_args)

        ws._re_read()
        output = workspace("setup", "--dry-run", global_args=global_args)

        assert "Test Phase" not in output
