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


def test_edit_deduction_modifier(mock_modifiers, mock_editor):
    """Test `ramble edit info` deduces it's a modifier"""
    edit("info")
    assert len(mock_editor) == 1
    assert "repos/builtin.mock/modifiers/info/modifier.py" in mock_editor[0]


def test_edit_singular_type(mock_modifiers, mock_editor):
    """Test `ramble edit -t modifier info` normalizes singular type"""
    edit("info", "-t", "modifier")
    assert len(mock_editor) == 1
    assert "repos/builtin.mock/modifiers/info/modifier.py" in mock_editor[0]


def test_edit_deduction_command(mock_editor):
    """Test `ramble edit edit` deduces it's a command"""
    edit("edit")
    assert len(mock_editor) == 1
    assert "ramble/cmd/edit.py" in mock_editor[0]


def test_edit_deduction_test(mock_editor):
    """Test `ramble edit cmd/edit` deduces it's a test"""
    edit("cmd/edit")
    assert len(mock_editor) == 1
    assert "ramble/test/cmd/edit.py" in mock_editor[0]


def test_edit_singular_type_with_spaces_hyphens(mock_editor):
    """Test package manager singular forms normalization with spaces/hyphens"""
    edit("spack", "-t", "package-manager")
    assert len(mock_editor) == 1
    assert "package_managers/spack/package_manager.py" in mock_editor[0]

    edit("spack", "-t", "package_manager")
    assert len(mock_editor) == 2
    assert "package_managers/spack/package_manager.py" in mock_editor[1]


def test_edit_unknown_type():
    with pytest.raises(KeyError):
        edit("-t", "unknown_type", "spack")


def test_edit_with_repo(mock_applications, mock_editor):
    import ramble.repository

    repo_path = ramble.repository.paths[ramble.repository.ObjectTypes.applications].repos[0].root
    edit("basic", "--repo", repo_path)
    assert len(mock_editor) == 1
    assert "repos/builtin.mock/applications/basic/application.py" in mock_editor[0]


def test_edit_with_namespace(mock_applications, mock_editor):
    edit("basic", "--namespace", "builtin.mock")
    assert len(mock_editor) == 1
    assert "repos/builtin.mock/applications/basic/application.py" in mock_editor[0]


def test_edit_deduction_docs(mock_editor):
    edit("index.rst")
    assert len(mock_editor) == 1
    assert "docs/index.rst" in mock_editor[0]


def test_edit_deduction_fails_correctly():
    output = edit("non-existent-object-name", fail_on_error=False)
    assert "No application for 'non-existent-object-name' was found" in output


def test_object_exists_exception():
    from ramble.cmd.edit import object_exists

    assert not object_exists("some_name", "invalid_type_name")


def test_normalize_type_name_empty():
    from ramble.cmd.edit import normalize_type_name

    assert normalize_type_name(None) is None
    assert normalize_type_name("") is None


def test_edit_object_is_directory(mock_applications, monkeypatch):

    import ramble.repository

    monkeypatch.setattr(
        ramble.repository.Repo, "filename_for_object_name", lambda self, name: self.root
    )
    output = edit("basic", fail_on_error=False)
    assert "is not a file!" in output


def test_edit_object_insufficient_permissions(mock_applications, monkeypatch):
    import os

    monkeypatch.setattr(os, "access", lambda path, mode: False)
    output = edit("basic", fail_on_error=False)
    assert "Insufficient permissions" in output


def test_edit_no_editor_found(mock_applications, monkeypatch):
    def mock_fail_editor(*args, **kwargs):
        raise TypeError("No editor")

    monkeypatch.setattr("ramble.cmd.edit.editor", mock_fail_editor)
    output = edit("basic", fail_on_error=False)
    assert "No valid editor was found" in output


def test_edit_multiple_files_found(monkeypatch):
    import glob

    monkeypatch.setattr(glob, "glob", lambda pattern: ["file1.py", "file2.py"])
    output = edit("-t", "command", "non-existent", fail_on_error=False)
    assert "Multiple files exist" in output
