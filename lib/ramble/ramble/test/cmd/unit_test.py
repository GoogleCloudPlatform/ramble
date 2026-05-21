# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import subprocess

import pytest

import ramble.paths
from ramble import main

pytestmark = pytest.mark.maybeslow

ramble_test = main.RambleCommand("unit-test")


def test_unit_test_list():
    output = ramble_test("--list")
    # Surely this file should show up in the list
    assert "ramble/test/cmd/unit_test.py" in output
    # But individual test should not show up
    assert "test_unit_test_list" not in output


def test_long_list():
    output = ramble_test("-L")
    assert "lib/ramble/ramble/test/cmd/unit_test.py::\n" in output
    assert "    test_long_list" in output


def test_full_list():
    output = ramble_test("-N")
    assert "lib/ramble/ramble/test/cmd/unit_test.py::test_full_list\n" in output


def test_pytest_help():
    output = ramble_test("-H")
    assert "-k EXPRESSION" in output
    assert "pytest-warnings:" in output
    assert "--collect-only" in output


@pytest.mark.parametrize(
    "extra_flag",
    [(""), ("--list")],
    ids=["main", "list"],
)
def test_failed_import(extra_flag):
    out = ramble_test(extra_flag, "-p", "fake-pytest", fail_on_error=False)
    assert "Ensure requirements-dev.txt are installed" in out


def test_list_only_lib():
    output = ramble_test("--lib", "-l")
    assert "var/ramble/repos" not in output
    assert "lib/ramble/ramble/test" in output


def test_list_only_objects():
    output = ramble_test("--obj", "-l")
    assert "var/ramble/repos" in output
    assert "lib/ramble/ramble/test" not in output


def test_external_repo_invalid():
    with pytest.raises(FileNotFoundError):
        ramble_test("--repo-path", "non-existent-path")


def test_external_repo_valid(tmpdir):
    test_dir = tmpdir.mkdir("test")
    test_file = test_dir.join("test_dummy.py")
    test_file.write("def test_dummy():\n    assert True\n")

    # Need to launch a new process due to how setup_analyze.py is handled differently
    # for Ramble repo and external repos.
    ramble_bin = os.path.join(ramble.paths.ramble_root, "bin", "ramble")
    result = subprocess.run(
        [ramble_bin, "unit-test", "--repo-path", str(tmpdir), "-k", "test_dummy"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "1 passed" in result.stdout


@pytest.mark.parametrize("flag", ["--perf", "--fast"])
def test_flags_accepted(flag):
    output = ramble_test(flag, "--list")
    assert "ramble/test/cmd/unit_test.py" in output


def test_slow_flag():
    output = ramble_test("--slow", "--list")
    assert "test_slow_flag" not in output
