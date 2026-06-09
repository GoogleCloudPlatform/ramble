# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")


def test_modeless_modifier_variables(
    workspace_name, mutable_mock_workspace_path, mutable_mock_apps_repo, mutable_mock_mods_repo
):
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()
        workspace(
            "manage",
            "experiments",
            "basic",
            "--wf",
            "test_wl",
            "-v",
            "n_nodes=1",
            "-v",
            "n_ranks=1",
            "-v",
            "modeless_required_var=val",
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        workspace(
            "manage",
            "modifiers",
            "--add",
            "--scope",
            "workspace",
            "-n",
            "test-mod",
            global_args=global_args,
        )

        template_path = os.path.join(ws.config_dir, "test.tpl")

        with open(template_path, "w+", encoding="utf-8") as f:
            f.write("{command}\n{modeless_variable}\n{modeless_var_mod}")

        workspace("setup", "--dry-run", global_args=global_args)

        rendered_path = os.path.join(ws.experiment_dir, "basic", "test_wl", "generated", "test")

        with open(rendered_path, encoding="utf-8") as f:
            data = f.read()
            assert "is defined" in data
            assert "MODELESS_ENV_VAR" in data
            assert "modeless_variable" not in data
            assert "modeless-append" in data
            assert "MODELESS_ENV_VAR_2=modeless_val" in data
