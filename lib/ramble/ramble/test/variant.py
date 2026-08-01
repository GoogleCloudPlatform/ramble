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
    "mutable_config",
    "mutable_mock_workspace_path",
    "mutable_mock_apps_repo",
    "mock_modifiers",
    "mock_base_applications",
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
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        ws._re_read()
        workspace("concretize", global_args=global_args)
        workspace("setup", "--dry-run", global_args=global_args)

        with open(ws.config_file_path, encoding="utf-8") as f:
            data = f.read()

            assert "zlib@1.2.11" not in data
            assert "zlib@1.2.12" in data

        script_path = os.path.join(
            ws.experiment_dir, "when-variants", "test_wl", "generated", "execute_experiment"
        )

        with open(script_path, encoding="utf-8") as f:
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
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        ws._re_read()
        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path, encoding="utf-8") as f:
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
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        config("add", "variants:zlib_type:testing", global_args=global_args)

        ws._re_read()
        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path, encoding="utf-8") as f:
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
            "--default-variable-value",
            "1",
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
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        config("add", "variants:inc_zlib:false", global_args=global_args)

        ws._re_read()
        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path, encoding="utf-8") as f:
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
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        ws._re_read()
        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path, encoding="utf-8") as f:
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

        with open(config_path, "w+", encoding="utf-8") as f:
            f.write(test_config)

        ws._re_read()
        workspace("concretize", "-f", global_args=global_args)

        with open(ws.config_file_path, encoding="utf-8") as f:
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
            "--default-variable-value",
            "1",
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

        with open(os.path.join(ws.config_dir, "variants.yaml"), "w+", encoding="utf-8") as f:
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
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        ws._re_read()
        exec_out = on("--executor='echo {leaf_value}'", global_args=global_args)

        assert test_value in exec_out


@pytest.mark.parametrize(
    "variant_scope,expected_bool,expected_val",
    [
        ("pkg_args", True, "one"),
        ("pkg_args", False, "two"),
        ("mod_pkg_args", True, "one"),
        ("mod_pkg_args", False, "two"),
    ],
)
def test_variant_expansion(workspace_name, variant_scope, expected_bool, expected_val):
    global_args = ["-w", workspace_name]

    app_env_name = "when-variants-{application::variant::bool}-{application::variant::val}"
    mod_env_name = "mod_package_with_args-{modifier::variant::bool}-{modifier::variant::val}"

    with ramble.workspace.create(workspace_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants@1.0",
            "--wf",
            "test_wl",
            "-e",
            "generated",
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

        config("add", f"variants:{variant_scope}:true", global_args=global_args)
        config("add", f"variants:bool:{expected_bool}", global_args=global_args)
        config("add", f"variants:val:{expected_val}", global_args=global_args)

        if variant_scope == "mod_pkg_args":
            with open(os.path.join(ws.config_dir, "modifiers.yaml"), "w+", encoding="utf-8") as f:
                f.write("""modifiers:
- name: spack-mod""")

        ws._re_read()
        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path, encoding="utf-8") as f:
            data = f.read()

            if variant_scope == "pkg_args":
                assert f"{app_env_name}:" in data
            elif variant_scope == "mod_pkg_args":
                assert f"{mod_env_name}:" in data

        b_spec = "+bool" if expected_bool else "~bool"
        v_spec = f"val={expected_val}"
        if variant_scope == "pkg_args":
            spack_spec = "when-variants@1.0 " + b_spec + " " + v_spec
        elif variant_scope == "mod_pkg_args":
            spack_spec = "mod_package@1.1 " + b_spec + " " + v_spec

        captured = workspace("info", "-v", global_args=global_args)

        assert spack_spec in captured


def test_repeat_variants_in_analyze(request):
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
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        ws._re_read()
        workspace("concretize", global_args=global_args)
        workspace("setup", "--dry-run", global_args=global_args)
        workspace("analyze", global_args=global_args)

        with open(os.path.join(ws.root, "results.latest.txt"), encoding="utf-8") as f:
            data = f.read()

            assert "is_repeat_parent" in data
            assert "is_repeat_child" in data
            assert "repeat_index" in data


@pytest.mark.parametrize(
    "var_value,should_fail",
    [
        (None, False),
        ("valid_val", False),
        ("invalid_val", True),
    ],
)
def test_templated_variant_validation(workspace_name, var_value, should_fail):
    ws_name = workspace_name
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
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        config(
            "add",
            "variants:templated_validation:'{templated_validation_var}'",
            global_args=global_args,
        )

        if var_value is not None:
            config(
                "add",
                f"variables:templated_validation_var:{var_value}",
                global_args=global_args,
            )

        ws._re_read()

        if should_fail:
            with pytest.raises(ramble.variants.RambleVariantError):
                workspace("concretize", global_args=global_args)
        else:
            workspace("concretize", global_args=global_args)


def test_variant_set_callable_validation():
    v_set = ramble.variants.VariantSet()

    def my_validator(val):
        return val in [1, 3, 5]

    v_set.default_variant("my_var", default=1, description="odd numbers", values=my_validator)

    # Check that it validates valid values
    v_set.experiment_variant("my_var", 3)
    defs = v_set.as_set()
    assert "my_var=3" in defs

    # Check invalid value raises error
    v_set2 = ramble.variants.VariantSet()
    v_set2.default_variant("my_var", default=1, description="odd numbers", values=my_validator)
    v_set2.experiment_variant("my_var", 2)

    with pytest.raises(ramble.variants.RambleVariantError):
        v_set2.as_set()


def test_variant_set_conditional_invalidation():
    """Test that the variant set cache is invalidated only when modified."""
    v_set = ramble.variants.VariantSet()
    v_set.default_variant("my_var", default=1)
    v_set.as_set()
    assert v_set._set_cache is not None

    v_set.default_variant("my_var", default=1)
    assert v_set._set_cache is not None

    v_set.default_variant("my_var", default=2)
    assert v_set._set_cache is None

    v_set.as_set()
    assert v_set._set_cache is not None

    v_set2 = ramble.variants.VariantSet()
    v_set2.default_variant("my_var", default=2)

    v_set.merge_default_variants(v_set2)
    assert v_set._set_cache is not None

    v_set3 = ramble.variants.VariantSet()
    v_set3.default_variant("other_var", default=3)

    v_set.merge_default_variants(v_set3)
    assert v_set._set_cache is None


def test_workload_group_variant(workspace_name):
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name):
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
            "-p",
            "spack",
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        info_out = workspace("info", "--variants", global_args=global_args)

        assert "workload_group=test_wl_group" in info_out
        assert "workload_group=all_workloads" in info_out
