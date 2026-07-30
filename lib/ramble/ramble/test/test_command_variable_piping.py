# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

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
