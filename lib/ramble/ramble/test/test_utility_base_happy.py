# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
import os
import shutil
import subprocess

import ramble.workspace
from ramble.utility.builtin.spack.utility import Spack


def test_utility_base_setup_runner_environment_exists(
    mutable_config, mutable_mock_workspace_path, monkeypatch, tmpdir
):
    ws = ramble.workspace.create("test_env_exists")
    ws.dry_run = False

    class MockAppInst:
        def __init__(self):
            self.variables = {"utility::spack::path": "/path/to/spack"}

        def satisfy_when(self, when_key):
            return True

    app_inst = MockAppInst()
    spack = Spack("/tmp/dummy")

    script_path = os.path.join(str(tmpdir), "source.sh")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write("export MY_TEST_VAR=1\n")

    spack.env_sources = {"True": [{"script_path": script_path, "when": []}]}

    env_mod = spack.setup_runner_environment(ws, app_inst)
    assert len(env_mod) > 0


def test_utility_base_validate_versions_happy(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    spack = Spack("/tmp/dummy")
    spack.provided_executables = {
        "spack": [
            {
                "executable": "spack",
                "version_cmd": "echo 1.5.0",
                "version_regex": r"(\d+\.\d+\.\d+)",
            }
        ]
    }

    def mock_which(cmd, **kwargs):
        if cmd == "spack":
            return "/path/to/spack/bin/spack"
        return None

    def mock_run(cmd_args, **kwargs):
        class MockResult:
            stdout = "1.5.0\n"
            stderr = ""
            returncode = 0

        return MockResult()

    monkeypatch.setattr(shutil, "which", mock_which)
    monkeypatch.setattr(subprocess, "run", mock_run)

    # Test happy path with both min and max
    res = spack.validate_versions(min_version="1.0.0", max_version="2.0.0")
    assert res is True

    # Test happy path with only min
    res = spack.validate_versions(min_version="1.0.0")
    assert res is True

    # Test happy path with only max
    res = spack.validate_versions(max_version="2.0.0")
    assert res is True
