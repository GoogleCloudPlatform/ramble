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
