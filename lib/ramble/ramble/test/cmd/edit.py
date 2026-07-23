# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.main import RambleCommand

edit = RambleCommand("edit")


@pytest.fixture
def mock_editor(monkeypatch):
    """Mock editor so we don't open a real one, using the _exec_func hook in spack.util.editor."""
    calls = []

    def mock_exec_func(exe, args):
        if args:
            calls.append(args[-1])

    def mocked_editor_wrapper(*args, **kwargs):
        kwargs["_exec_func"] = mock_exec_func
        from spack.util.editor import editor as real_editor

        real_editor(*args, **kwargs)

    monkeypatch.setattr("ramble.cmd.edit.editor", mocked_editor_wrapper)

    return calls


def test_edit_command(mock_editor):
    """Test `ramble edit -t command <cmd>`"""
    edit("-t", "command", "edit")
    assert len(mock_editor) == 1
    assert "ramble/cmd/edit.py" in mock_editor[0]


def test_edit_test(mock_editor):
    """Test `ramble edit -t test <test>`"""
    edit("-t", "test", "cmd/edit")
    assert len(mock_editor) == 1
    assert "ramble/test/cmd/edit.py" in mock_editor[0]


def test_edit_module(mock_editor):
    """Test `ramble edit -t module <module>`"""
    edit("-t", "module", "config")
    assert len(mock_editor) == 1
    assert "ramble/config.py" in mock_editor[0]


def test_edit_docs(mock_editor):
    """Test `ramble edit -t docs <doc>`"""
    edit("-t", "docs", "index.rst")
    assert len(mock_editor) == 1
    assert "docs/index.rst" in mock_editor[0]


def test_edit_file_not_found():
    output = edit("-t", "command", "non-existent-cmd", fail_on_error=False)
    assert "No file for 'non_existent_cmd' was found" in output


def test_edit_application(mock_applications, mock_editor):
    edit("basic")
    assert len(mock_editor) == 1
    assert "repos/builtin.mock/applications/basic/application.py" in mock_editor[0]


def test_edit_modifier(mock_modifiers, mock_editor):
    edit("info", "-t", "modifiers")
    assert len(mock_editor) == 1
    assert "repos/builtin.mock/modifiers/info/modifier.py" in mock_editor[0]
