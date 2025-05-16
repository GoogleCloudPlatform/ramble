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
from ramble.error import RambleCommandError
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "mutable_mock_apps_repo",
    "mock_modifiers",
)

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


def test_fom_context_enabled_when_true(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    test_output = """
test when context 4.2
test when fom 5.6 test always 3.5
test inheritance 12.0
"""

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

        ws.write()

        output_path = os.path.join(
            ws.experiment_dir, "when-directives", "test_wl", "generated", "test.out"
        )
        results_path = os.path.join(ws.root, "results.latest.txt")

        workspace("setup", global_args=global_args)

        with open(output_path, "w+") as f:
            f.write(test_output)

        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "test always context" in results
            assert "3.5" in results
            assert "test when context" not in results
            assert "4.2" not in results

        config("add", "variants:register_fom_context_when:true", global_args=global_args)

        ws._re_read()
        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "test always context" in results
            assert "3.5" in results
            assert "test when context" in results
            assert "4.2" in results


def test_fom_enabled_when_true(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    test_output = """
test when context 4.2
test when fom 5.6 test always 3.5
test inheritance 12.0
"""

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

        ws.write()

        output_path = os.path.join(
            ws.experiment_dir, "when-directives", "test_wl", "generated", "test.out"
        )
        results_path = os.path.join(ws.root, "results.latest.txt")

        workspace("setup", global_args=global_args)

        with open(output_path, "w+") as f:
            f.write(test_output)

        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "test always context" in results
            assert "3.5" in results
            assert "test_fom_when" not in results
            assert "5.6" not in results

        config("add", "variants:register_fom_context_when:true", global_args=global_args)
        config("add", "variants:register_fom_when:true", global_args=global_args)

        ws._re_read()
        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "test always context" in results
            assert "4.2" in results
            assert "test_fom_when" in results
            assert "5.6" in results


def test_fom_errors_when_context_not_found(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    test_output = """
test when context 4.2
test when fom 5.6 test always 3.5
test inheritance 12.0
"""

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

        ws.write()

        output_path = os.path.join(
            ws.experiment_dir, "when-directives", "test_wl", "generated", "test.out"
        )
        results_path = os.path.join(ws.root, "results.latest.txt")

        workspace("setup", global_args=global_args)

        with open(output_path, "w+") as f:
            f.write(test_output)

        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "test always context" in results
            assert "3.5" in results

        config("add", "variants:register_fom_when:true", global_args=global_args)

        ws._re_read()

        with pytest.raises(RambleCommandError):

            captured = workspace("analyze", global_args=global_args)
            assert "context 'test_context_when'" in captured


def test_same_fom_name_different_context(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    test_output = """
'Always' fom in always context is decimal, 'always' fom in when context is integer
test when context 4.2
test when fom 5.6 test always 3.5
test inheritance 12.0
"""

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

        ws.write()

        output_path = os.path.join(
            ws.experiment_dir, "when-directives", "test_wl", "generated", "test.out"
        )
        results_path = os.path.join(ws.root, "results.latest.txt")

        ws._re_read()
        workspace("setup", global_args=global_args)

        with open(output_path, "w+") as f:
            f.write(test_output)

        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "test always context" in results
            assert "3.5" in results
            assert "test when context" not in results
            assert "5.6" not in results

        config("add", "variants:register_fom_context_when:true", global_args=global_args)

        ws._re_read()
        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "test always context" in results
            assert "3.5" in results
            assert "test when context" in results
            assert "3 integer" in results


def test_fom_overwrites_when_inherited(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    test_output = """
Parent FOM regex is decimal, child FOM regex is integer and should clobber parent FOM
test when context 4.2
test when fom 5.6 test always 3.5
test inheritance 12.0
"""

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-directives-inherited",
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

        ws.write()

        output_path = os.path.join(
            ws.experiment_dir, "when-directives-inherited", "test_wl", "generated", "test.out"
        )
        results_path = os.path.join(ws.root, "results.latest.txt")

        ws._re_read()
        workspace("setup", global_args=global_args)

        with open(output_path, "w+") as f:
            f.write(test_output)

        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "test always context" in results
            assert "3.5" in results
            assert "test inheritance context" not in results
            assert "12 integer" not in results

        config("add", "variants:register_inherited_fom_when:true", global_args=global_args)

        ws._re_read()

        output = workspace("analyze", global_args=global_args)

        assert "Overwriting with new definition from when-directives-inherited" in output

        with open(results_path) as f:
            results = f.read()

            assert "test always context" not in results
            assert "3.5" not in results
            assert "test inheritance context" in results
            assert "12 integer" in results
            assert "12.0" not in results


@pytest.mark.parametrize(
    "validator_value,fails",
    [
        (True, True),
        (False, False),
    ],
)
def test_register_validator_when(request, validator_value, fails):
    from ramble.application import ObjectValidationError

    ws_name = request.node.name.replace("[", "_").replace("]", "_")

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "zlib_path=/not/a/path",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            global_args=global_args,
        )

        config("add", "variants:inc_zlib:True", global_args=global_args)
        config("add", "variants:zlib_type:preferred", global_args=global_args)
        config("add", f"variants:validation:{validator_value}", global_args=global_args)

        ws._re_read()

        failed = False
        try:
            workspace("setup", global_args=global_args)
        except ObjectValidationError:
            failed = True

        if not fails:
            assert not failed
        else:
            assert failed


@pytest.mark.parametrize(
    "inc_value,type_value",
    [
        (True, "preferred"),
        (True, "testing"),
        (True, "modifier"),
        (False, "preferred"),
    ],
)
def test_formatted_exec_when(request, inc_value, type_value):
    ws_name = request.node.name.replace("[", "_").replace("]", "_")

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "zlib_path=/not/a/path",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            global_args=global_args,
        )

        config("add", f"variants:inc_zlib:{inc_value}", global_args=global_args)
        config("add", f"variants:zlib_type:{type_value}", global_args=global_args)

        if inc_value:
            inc_str = f"included with type of {type_value}"
        else:
            inc_str = "not included"
        test_str = f"     from_variant zlib {inc_str}"

        ws._re_read()
        workspace("setup", global_args=global_args)

        exec_file = os.path.join(
            ws.experiment_dir,
            "when-variants",
            "test_wl",
            "generated",
            "execute_experiment",
        )

        with open(exec_file) as f:
            data = f.read()

            assert test_str in data
            assert "{test_formatted_exec}" not in data


@pytest.mark.parametrize(
    "workload_name",
    ["test_wl", "test_unset_wl"],
)
def test_variable_when_workload_constraint(request, workload_name):
    ws_name = request.node.name.replace("[", "_").replace("]", "_")

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            workload_name,
            "-v",
            "zlib_path=/not/a/path",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            global_args=global_args,
        )

        if workload_name == "test_wl":
            test_str = "Test when workload variable is_defined"
        else:
            test_str = "Test when workload variable {test_when_var}"

        ws._re_read()
        workspace("setup", global_args=global_args)

        exec_file = os.path.join(
            ws.experiment_dir,
            "when-variants",
            workload_name,
            "generated",
            "execute_experiment",
        )

        with open(exec_file) as f:
            data = f.read()

            assert test_str in data


@pytest.mark.parametrize(
    "inc_value,type_value",
    [
        (True, "preferred"),
        (True, "testing"),
        (True, "modifier"),
        (False, "preferred"),
    ],
)
def test_variable_when(request, inc_value, type_value):
    ws_name = request.node.name.replace("[", "_").replace("]", "_")

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "zlib_path=/not/a/path",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            global_args=global_args,
        )

        config("add", f"variants:inc_zlib:{inc_value}", global_args=global_args)
        config("add", f"variants:zlib_type:{type_value}", global_args=global_args)

        if inc_value:
            test_str = f"Standard was {type_value}"
        else:
            test_str = "Standard was unincluded"

        ws._re_read()
        workspace("setup", global_args=global_args)

        exec_file = os.path.join(
            ws.experiment_dir,
            "when-variants",
            "test_wl",
            "generated",
            "execute_experiment",
        )

        with open(exec_file) as f:
            data = f.read()

            assert test_str in data


@pytest.mark.parametrize(
    "inc_value",
    [True, False],
)
def test_package_manager_variable_when(request, inc_value, mutable_mock_pkg_mans_repo):
    ws_name = request.node.name.replace("[", "_").replace("]", "_")

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "zlib_path=/not/a/path",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "when-package-manager",
            global_args=global_args,
        )

        config("add", f"variants:package_manager_included:{inc_value}", global_args=global_args)

        if inc_value:
            test_str = "PM test: included"
        else:
            test_str = "PM test: {pm_var_test}"

        ws._re_read()
        workspace("setup", global_args=global_args)

        exec_file = os.path.join(
            ws.experiment_dir,
            "when-variants",
            "test_wl",
            "generated",
            "execute_experiment",
        )

        with open(exec_file) as f:
            data = f.read()

            assert test_str in data


@pytest.mark.parametrize(
    "inc_value",
    [True, False],
)
def test_workflow_manager_variable_when(request, inc_value, mutable_mock_wms_repo):
    ws_name = request.node.name.replace("[", "_").replace("]", "_")

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "zlib_path=/not/a/path",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "--wm",
            "when-workflow-manager",
            global_args=global_args,
        )

        config("add", f"variants:workflow_manager_included:{inc_value}", global_args=global_args)

        if inc_value:
            test_str = "WM test: included"
        else:
            test_str = "WM test: {wm_var_test}"

        ws._re_read()
        workspace("setup", global_args=global_args)

        exec_file = os.path.join(
            ws.experiment_dir,
            "when-variants",
            "test_wl",
            "generated",
            "execute_experiment",
        )

        with open(exec_file) as f:
            data = f.read()

            assert test_str in data


@pytest.mark.parametrize(
    "inc_value",
    [True, False],
)
def test_modifier_variable_when(request, inc_value, mutable_mock_mods_repo):
    ws_name = request.node.name.replace("[", "_").replace("]", "_")

    global_args = ["-w", ws_name]

    with ramble.workspace.create(ws_name) as ws:

        workspace(
            "manage",
            "experiments",
            "when-variants",
            "--wf",
            "test_wl",
            "-v",
            "zlib_path=/not/a/path",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            global_args=global_args,
        )

        config_path = os.path.join(ws.config_dir, "modifiers.yaml")
        with open(config_path, "w+") as f:
            f.write("modifiers:\n")
            f.write(" - name: when-modifier\n")

        config("add", f"variants:modifier_included:{inc_value}", global_args=global_args)

        if inc_value:
            test_str = "MOD test: included"
        else:
            test_str = "MOD test: {mod_var_test}"

        ws._re_read()
        workspace("setup", global_args=global_args)

        exec_file = os.path.join(
            ws.experiment_dir,
            "when-variants",
            "test_wl",
            "generated",
            "execute_experiment",
        )

        with open(exec_file) as f:
            data = f.read()

            assert test_str in data


def test_success_criteria_when(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    test_output = """
test when context 4.2
test when fom 5.6 test always 3.5
test inheritance 12.0
"""

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

        ws.write()

        output_path = os.path.join(
            ws.experiment_dir, "when-directives", "test_wl", "generated", "test.out"
        )
        results_path = os.path.join(ws.root, "results.latest.txt")

        workspace("setup", global_args=global_args)

        with open(output_path, "w+") as f:
            f.write(test_output)

        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "FAILED" not in results
            assert "SUCCESS" in results

        config("add", "variants:success_criteria_when:true", global_args=global_args)

        ws._re_read()
        workspace("analyze", global_args=global_args)

        with open(results_path) as f:
            results = f.read()

            assert "FAILED" in results
            assert "SUCCESS" not in results


def test_register_template_when(request):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    test_template = """
echo "test template for {experiment_name}"
"""

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

        ws.write()

        template_src_path = os.path.join(ws.shared_dir, "test_template.tpl")
        template_dest_path = os.path.join(
            ws.experiment_dir, "when-directives", "test_wl", "generated", "test_template"
        )

        workspace("setup", global_args=global_args)

        with open(template_src_path, "w+") as f:
            f.write(test_template)

        workspace("setup", global_args=global_args)

        assert not os.path.exists(template_dest_path)

        config("add", "variants:register_template_when:true", global_args=global_args)

        ws._re_read()
        workspace("setup", global_args=global_args)

        assert os.path.exists(template_dest_path)

        with open(template_dest_path) as f:
            generated_template = f.read()

            assert "test template for generated" in generated_template
