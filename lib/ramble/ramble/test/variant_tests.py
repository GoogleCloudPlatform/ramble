# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import pytest

import ramble.variants
import ramble.workspace
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config", "mutable_mock_workspace_path", "mutable_mock_apps_repo"
)

config = RambleCommand("config")
workspace = RambleCommand("workspace")


def test_default_arg_works(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        ws._re_read()
        workspace("concretize", global_args=global_args)
        workspace("setup", "--dry-run", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()

            assert "zlib@1.2.11" not in data
            assert "zlib@1.2.12" in data

        script_path = os.path.join(
            ws.experiment_dir, "when-variants", "test_wl", "generated", "execute_experiment"
        )

        with open(script_path) as f:
            data = f.read()

            assert "echo 'Test'" in data


def test_default_variant_value_works_with_when(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        ws._re_read()
        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()

            assert "zlib@1.2.11" not in data
            assert "zlib@1.2.12" in data


def test_changed_variant_value_works_with_when(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        config("add", "variants:zlib_type:testing", global_args=global_args)

        ws._re_read()
        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()

            assert "zlib@1.2.11" in data
            assert "zlib@1.2.12" not in data


def test_invalid_variant_value_errors(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        config("add", "variants:zlib_type:invalid", global_args=global_args)

        ws._re_read()

        with pytest.raises(ramble.variants.RambleVariantError):
            workspace("concretize", global_args=global_args)


def test_boolean_variants(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        config("add", "variants:inc_zlib:false", global_args=global_args)

        ws._re_read()
        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()

            assert "zlib@1.2.11" not in data
            assert "zlib@1.2.12" not in data
