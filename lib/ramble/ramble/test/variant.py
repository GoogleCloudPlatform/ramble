# Copyright 2022-2026 The Ramble Authors
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
    "mutable_config", "mutable_mock_workspace_path", "mutable_mock_apps_repo", "mock_modifiers"
)

config = RambleCommand("config")
workspace = RambleCommand("workspace")
on = RambleCommand("on")


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


def test_non_matched_variants_are_ignored(request):
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
            "pip",
            global_args=global_args,
        )

        ws._re_read()
        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()

            assert "zlib" not in data


@pytest.mark.parametrize(
    "test_name,mode,expected_spec",
    [
        ("when_modifier", "test", "zlib@1.2.13"),
        ("when_modifier_mode", "exp-scope", "mod_mode_pkg@2.1"),
    ],
)
def test_modifier_variants_works_with_when(
    test_name,
    mode,
    expected_spec,
    mutable_mock_workspace_path,
    mutable_mock_apps_repo,
    mock_modifiers,
):
    workspace_name = test_name
    global_args = ["-w", workspace_name]

    test_config = f"""
ramble:
  variants:
    package_manager: spack
    zlib_type: modifier
    inc_zlib: true
  variables:
    mpi_command: ''
    batch_submit: 'batch_submit {{execute_experiment}}'
    processes_per_node: 1
    modeless_required_var: 1
  applications:
    when-variants:
      workloads:
        test_wl:
          experiments:
            test:
              variables:
                n_ranks: 1
                n_nodes: 1
                processes_per_node: 1
  modifiers:
  - name: test-mod
    mode: {mode}
"""

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws._re_read()
        workspace("concretize", "-f", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()
            assert expected_spec in data


def test_variant_info_works(request):
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
        info_out = workspace("info", "--variants", global_args=global_args)

        assert "application_name=when-variants" in info_out
        assert "indirect_variant=test-value" in info_out


@pytest.mark.parametrize("test_value", ["value1", "value2", "value3"])
def test_variant_nesting_works(workspace_name, test_value):
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        with open(os.path.join(ws.config_dir, "variants.yaml"), "w+") as f:
            f.write(f"""variants:
  iterative_variant: {test_value}
  iterative_variant2: {test_value}""")
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
        exec_out = on("--executor='echo {leaf_value}'", global_args=global_args)

        assert test_value in exec_out
