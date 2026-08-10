# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from unittest.mock import patch

from ramble.definitions.variables import CommandVariable


class MockWorkspace:
    def __init__(self):
        self.dry_run = False
        self.object_command_cache = {}


class MockExpander:
    def expand_var(self, value):
        return value


class MockAppInst:
    def __init__(self):
        self.expander = MockExpander()

    def register_missing_command_variable(self, var):
        pass


def test_command_variable_pipeline_escaping():
    workspace = MockWorkspace()
    app_inst = MockAppInst()

    # This command uses a pipeline and single quotes with awk.
    # Legacy parser incorrectly tokenizes and fragments this, causing a syntax error in awk.
    cmd_var = CommandVariable(
        name="test_pipeline",
        command="echo \"hello world\" | awk '{print $1}'",
        dry_run_value="dry_run_default",
    )

    extracted_val = cmd_var.extract_value(workspace, app_inst)

    # The correct shell output is 'hello'.
    assert extracted_val == "hello"


def test_command_variable_logical_chaining():
    workspace = MockWorkspace()
    app_inst = MockAppInst()

    # Test conditional command chaining using && and sequential execution using ;
    cmd_var = CommandVariable(
        name="test_chaining",
        command="printf 'hello' && printf ' ' ; printf 'world'",
        dry_run_value="dry_run_default",
    )

    extracted_val = cmd_var.extract_value(workspace, app_inst)
    assert extracted_val == "hello world"


def test_command_variable_stderr_redirection():
    workspace = MockWorkspace()
    app_inst = MockAppInst()

    # Test stderr redirection to stdout so it gets captured
    cmd_var = CommandVariable(
        name="test_redirection",
        command="sh -c 'echo \"error msg\" >&2' 2>&1",
        dry_run_value="dry_run_default",
    )

    extracted_val = cmd_var.extract_value(workspace, app_inst)
    assert extracted_val == "error msg"


def test_command_variable_cache_hit():
    workspace = MockWorkspace()
    app_inst = MockAppInst()

    cmd_var = CommandVariable(
        name="test_cache",
        command="echo 'value1'",
        dry_run_value="dry_run_default",
    )

    # First call evaluates and caches the result
    val1 = cmd_var.extract_value(workspace, app_inst)
    assert val1 == "value1"
    assert "echo 'value1'" in workspace.object_command_cache

    # Manually modify cache to test that the next extract_value uses the cache
    workspace.object_command_cache["echo 'value1'"] = "cached_value"
    val2 = cmd_var.extract_value(workspace, app_inst)
    assert val2 == "cached_value"


def test_command_variable_non_zero_exit():
    workspace = MockWorkspace()
    app_inst = MockAppInst()

    cmd_var = CommandVariable(
        name="test_non_zero",
        command="false",
        dry_run_value="dry_run_default",
    )

    # false command exits with 1, should evaluate to empty string (no stdout)
    val = cmd_var.extract_value(workspace, app_inst)
    assert val == ""


def test_command_variable_exception_handling():
    workspace = MockWorkspace()
    app_inst = MockAppInst()

    cmd_var = CommandVariable(
        name="test_exception",
        command="echo 'test'",
        dry_run_value="dry_run_default",
    )

    # Mock subprocess.Popen to raise an OSError
    with patch("subprocess.Popen", side_effect=OSError("mock error")):
        val = cmd_var.extract_value(workspace, app_inst)
        # Exception handler should catch the OSError and return self.dry_run_value
        assert val == "dry_run_default"
