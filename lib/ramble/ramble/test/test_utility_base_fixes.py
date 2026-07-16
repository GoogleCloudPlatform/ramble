# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def test_utility_base_environment_modifications(mutable_config, mutable_mock_workspace_path):
    import ramble.workspace
    from ramble.utility.builtin.spack.utility import Spack

    ws = ramble.workspace.create("test_env")
    ws.dry_run = True

    class MockAppInst:
        def __init__(self):
            self.variables = {"utility::spack::path": "/path/to/spack"}

        def satisfy_when(self, when_key):
            return when_key == "True" or when_key is True

    app_inst = MockAppInst()
    spack = Spack("/tmp/dummy")

    # Manually insert env modifications with when keys
    spack.env_sources = {
        "True": [{"script_path": "source.sh", "when": []}],
        "False": [{"script_path": "no.sh", "when": []}],
    }
    spack.env_sets = {
        "True": [{"var": "A", "value": "1", "when": []}],
        "False": [{"var": "B", "value": "2", "when": []}],
    }
    spack.env_prepends = {
        "True": [{"var": "C", "value": "1", "when": []}],
        "False": [{"var": "D", "value": "2", "when": []}],
    }
    spack.env_appends = {
        "True": [{"var": "E", "value": "1", "when": []}],
        "False": [{"var": "F", "value": "2", "when": []}],
    }

    spack.setup_runner_environment(ws, app_inst)

    act_cmd = spack.get_experiment_activation_command(ws, app_inst)

    assert "source.sh" in act_cmd
    assert "no.sh" not in act_cmd
    assert "export A=1" in act_cmd
    assert "export B=2" not in act_cmd
    assert "export C=1:$C" in act_cmd
    assert "export D=2:$D" not in act_cmd
    assert "export E=$E:1" in act_cmd
    assert "export F=$F:2" not in act_cmd


def test_utility_base_validate_versions(mutable_config, mutable_mock_workspace_path, monkeypatch):
    import ramble.workspace
    from ramble.utility.builtin.spack.utility import Spack

    ramble.workspace.create("test_validate")

    spack = Spack("/tmp/dummy")
    spack.provided_executables = {
        "spack": [
            {
                "executable": "spack",
                "version_cmd": "echo 1.2.3",
                "version_regex": r"(\d+\.\d+\.\d+)",
            }
        ]
    }

    import shutil
    import subprocess

    original_which = shutil.which

    def mock_which(cmd, **kwargs):
        if cmd == "spack":
            return "/path/to/spack/bin/spack"
        return original_which(cmd, **kwargs)

    def mock_run(cmd_args, **kwargs):
        class MockResult:
            stdout = "1.2.3\n"
            stderr = ""
            returncode = 0

        return MockResult()

    monkeypatch.setattr(shutil, "which", mock_which)
    monkeypatch.setattr(subprocess, "run", mock_run)

    res = spack.validate_versions(min_version="1.0.0", max_version="2.0.0")
    print(spack.availability_error)
    assert res is True
