# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.paths
from ramble import main
from ramble.cmd import style

style_cmd = main.RambleCommand("style")


@pytest.mark.parametrize("tool", style.tool_names)
def test_style(tool):
    out = style_cmd("--tool", tool, __file__)
    assert f"{tool} checks were clean" in out


@pytest.mark.parametrize(
    "content,expected_err",
    [
        ("import b\nimport a", "Imports are incorrectly sorted"),
    ],
)
def test_style_with_error(tmpdir, content, expected_err):
    with tmpdir.as_cwd():
        new_file = "new_file.py"
        with open(new_file, "w+") as f:
            f.write(content)

        out = style_cmd(new_file, fail_on_error=False)
        assert style_cmd.returncode != 0
        assert expected_err in out


def test_changed_files_all():
    files = style.changed_files(all_files=True)
    # Currently there are more than 900 files checked for styling.
    # Use a smaller number here.
    assert len(files) > 500


def test_skip_tools():
    output = style_cmd("--skip", ",".join(style.tool_names))
    assert "Nothing to run" in output


def test_black_version_mismatch(capsys):
    class MockExecutable:
        def __init__(self, output):
            self.output = output
            self.returncode = 0

        def __call__(self, *args, **kwargs):
            return self.output

    mock_black = MockExecutable("black, 25.0.0")

    class MockArgs:
        fix = False
        root_relative = False
        repo_path = None

    args = MockArgs()

    style.run_black(mock_black, [], args)

    captured = capsys.readouterr()
    assert "WARNING: black version is 25.0.0" in captured.err
    assert (
        f"but the version used for the PR style test is {style._BLACK_GOLDEN_VERSION}"
        in captured.err
    )


def test_style_invalid_repo(tmpdir):
    with tmpdir.as_cwd():
        out = style_cmd("--repo-path", str(tmpdir), fail_on_error=False)
        assert style_cmd.returncode != 0
        assert "is not a valid Ramble repository" in out


def test_style_valid_repo():
    builtin_mock_repo = os.path.join(ramble.paths.prefix, "var", "ramble", "repos", "builtin.mock")
    out = style_cmd("--repo-path", builtin_mock_repo)
    assert "style checks were clean" in out


def test_changed_files_git_failure(tmpdir):
    file1 = tmpdir.join("file1.py")
    file1.write("import os")
    file2 = tmpdir.join("file2.py")
    file2.write("import sys")

    files = style.changed_files(root=str(tmpdir))

    assert "file1.py" in files
    assert "file2.py" in files
