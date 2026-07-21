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

import pytest

import ramble.filters
import ramble.pipeline
import ramble.workspace
from ramble.utility.builtin.spack.utility import Spack


def test_utility_base_validate_versions_regex_fails(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    spack = Spack("/tmp/dummy")
    spack.provided_executables = {
        "spack": [
            {"executable": "spack", "version_cmd": "echo bad", "version_regex": r"(\d+\.\d+\.\d+)"}
        ]
    }
    monkeypatch.setattr(shutil, "which", lambda cmd, **kwargs: "/path/to/spack")

    class MockResult:
        stdout = "bad\n"
        stderr = ""
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: MockResult())
    assert spack.validate_versions(min_version="1.0.0") is False
    assert "Could not determine version" in spack.availability_error


def test_utility_base_validate_versions_less_than_min(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    spack = Spack("/tmp/dummy")
    spack.provided_executables = {
        "spack": [
            {
                "executable": "spack",
                "version_cmd": "echo 1.0.0",
                "version_regex": r"(\d+\.\d+\.\d+)",
            }
        ]
    }
    monkeypatch.setattr(shutil, "which", lambda cmd, **kwargs: "/path/to/spack")

    class MockResult:
        stdout = "1.0.0\n"
        stderr = ""
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: MockResult())
    assert spack.validate_versions(min_version="1.5.0") is False
    assert "is less than required minimum" in spack.availability_error


def test_utility_base_validate_versions_greater_than_max(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    spack = Spack("/tmp/dummy")
    spack.provided_executables = {
        "spack": [
            {
                "executable": "spack",
                "version_cmd": "echo 2.0.0",
                "version_regex": r"(\d+\.\d+\.\d+)",
            }
        ]
    }
    monkeypatch.setattr(shutil, "which", lambda cmd, **kwargs: "/path/to/spack")

    class MockResult:
        stdout = "2.0.0\n"
        stderr = ""
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: MockResult())
    assert spack.validate_versions(max_version="1.5.0") is False
    assert "is greater than required maximum" in spack.availability_error


def test_utility_base_validate_versions_shutil_fails(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    spack = Spack("/tmp/dummy")
    spack.provided_executables = {"spack": [{"executable": "spack"}]}
    monkeypatch.setattr(shutil, "which", lambda cmd, **kwargs: None)
    assert spack.validate_versions() is False
    assert "not found in PATH" in spack.availability_error


def test_utility_base_validate_versions_no_executables(
    mutable_config, mutable_mock_workspace_path
):
    spack = Spack("/tmp/dummy")
    spack.provided_executables = {}
    assert spack.validate_versions() is False
    assert "No provided executables defined" in spack.availability_error


def test_utility_base_validate_versions_run_fails(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    spack = Spack("/tmp/dummy")
    spack.provided_executables = {
        "spack": [{"executable": "spack", "version_cmd": "fail", "version_regex": ".*"}]
    }
    monkeypatch.setattr(shutil, "which", lambda cmd, **kwargs: "/path")

    def mock_run_fail(*args, **kwargs):
        raise Exception("Run failed")

    monkeypatch.setattr(subprocess, "run", mock_run_fail)
    assert spack.validate_versions(min_version="1.0") is False
    assert "Error checking version" in spack.availability_error


def test_utility_base_setup_runner_environment_system(mutable_config, mutable_mock_workspace_path):
    ws = ramble.workspace.create("test_sys")

    class MockAppInst:
        variables = {"utility::spack::path": "system"}

        def satisfy_when(self, when_key):
            return True

    app_inst = MockAppInst()
    spack = Spack("/tmp/dummy")
    env_mod = spack.setup_runner_environment(ws, app_inst)
    assert len(env_mod) == 0
    assert spack.get_experiment_activation_command(ws, app_inst) == ""


def test_utility_base_setup_runner_environment_missing_script(
    mutable_config, mutable_mock_workspace_path
):
    ws = ramble.workspace.create("test_miss")
    ws.dry_run = False

    class MockAppInst:
        variables = {"utility::spack::path": "/path/to/spack"}

        def satisfy_when(self, when_key):
            return True

    app_inst = MockAppInst()
    spack = Spack("/tmp/dummy")
    spack.env_sources = {"True": [{"script_path": "/missing/script.sh", "when": []}]}
    # This should log a warning but not fail
    spack.setup_runner_environment(ws, app_inst)


def test_utility_base_map_fetch_kwargs(mutable_config, mutable_mock_workspace_path):
    spack = Spack("/tmp/dummy")
    spack.fetch_mappings = {None: [{"utility_var": "git", "fetch_var": "url", "fallback_for": []}]}
    mapped = spack.map_fetch_kwargs({"git": "my_git_url"})
    assert mapped == {"url": "my_git_url"}


def test_application_base_bootstrap_utilities_is_available_true(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    ws = ramble.workspace.create("test_avail")
    os.makedirs(os.path.dirname(ws.config_file_path), exist_ok=True)
    with open(ws.config_file_path, "w", encoding="utf-8") as f:
        f.write("""ramble:
  config:
    bootstrap_utilities: True
  variables:
    use_system_spack: True
  applications:
    hostname:
      workloads:
        serial:
          experiments:
            test_exp:
              variables:
                n_ranks: '1'
  utilities:
    spack:
      git: mygit
""")
    ws._re_read()
    filters = ramble.filters.Filters()
    with ws:
        setup_pipeline = ramble.pipeline.SetupPipeline(ws, filters)
        app_inst = next(iter(setup_pipeline.experiment_set.experiments.values()))
        app_inst.required_utilities = {frozenset([]): {"spack": {"git": "mygit"}}}
        monkeypatch.setattr(
            shutil, "which", lambda cmd, **kwargs: "/path/to/spack" if cmd == "spack" else None
        )
        setup_pipeline.run()
    assert app_inst.variables.get("utility::spack::path") == "system"


def test_application_base_bootstrap_utilities_is_bootstrappable_false(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    ws = ramble.workspace.create("test_boot")
    os.makedirs(os.path.dirname(ws.config_file_path), exist_ok=True)
    with open(ws.config_file_path, "w", encoding="utf-8") as f:
        f.write("""ramble:
  config:
    bootstrap_utilities: True
  applications:
    hostname:
      workloads:
        serial:
          experiments:
            test_exp:
              variables:
                n_ranks: '1'
  utilities:
    spack:
      git: mygit
""")
    ws._re_read()
    filters = ramble.filters.Filters()
    with ws:
        setup_pipeline = ramble.pipeline.SetupPipeline(ws, filters)
        app_inst = next(iter(setup_pipeline.experiment_set.experiments.values()))
        app_inst.required_utilities = {frozenset([]): {"spack": {"git": "mygit"}}}
        UtilityBase = ramble.repository.get_base_class("utility-base")
        monkeypatch.setattr(UtilityBase, "is_available", lambda *a, **k: False)
        # Mock bootstrappable to False
        monkeypatch.setattr(
            UtilityBase, "bootstrappable", {"True": [{"is_bootstrappable": False}]}
        )
        monkeypatch.setattr(
            UtilityBase, "missing_error_messages", {"True": [{"message": "Custom Error"}]}
        )

        with pytest.raises(SystemExit):
            setup_pipeline.run()
        # Custom Error should have been logged


def test_application_base_bootstrap_utilities_success(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    ws = ramble.workspace.create("test_succ")
    os.makedirs(os.path.dirname(ws.config_file_path), exist_ok=True)
    with open(ws.config_file_path, "w", encoding="utf-8") as f:
        f.write("""ramble:
  config:
    bootstrap_utilities: True
  applications:
    hostname:
      workloads:
        serial:
          experiments:
            test_exp:
              variables:
                n_ranks: '1'
  utilities:
    spack:
      git: mygit
""")
    ws._re_read()
    filters = ramble.filters.Filters()
    with ws:
        setup_pipeline = ramble.pipeline.SetupPipeline(ws, filters)
        app_inst = next(iter(setup_pipeline.experiment_set.experiments.values()))
        app_inst.required_utilities = {frozenset([]): {"spack": {"git": "mygit"}}}
        UtilityBase = ramble.repository.get_base_class("utility-base")
        monkeypatch.setattr(UtilityBase, "is_available", lambda *a, **k: False)
        # Force fetch
        ws.dry_run = False

        class MockStage:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def set_subdir(self, subdir):
                pass

            def fetch(self):
                pass

            def expand_archive(self):
                pass

        monkeypatch.setattr(ramble.stage, "InputStage", MockStage)
        monkeypatch.setattr(UtilityBase, "validate_versions", lambda *a, **k: True)

        setup_pipeline.run()
    assert hasattr(app_inst, "_bootstrapped_utility_paths")
    assert "spack" in app_inst._bootstrapped_utility_paths
