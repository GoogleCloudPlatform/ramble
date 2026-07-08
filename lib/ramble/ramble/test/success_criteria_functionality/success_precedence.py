# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")
ramble_on = RambleCommand("on")


def test_success_criteria_precedence(mock_applications, workspace_name):
    """
    Tests that YAML success_criteria takes precedence over
    object-defined criteria
    """
    test_config = """
ramble:
  variables:
    processes_per_node: '1'
    n_threads: '1'
  applications:
    success-criteria-conflicts:
      workloads:
        success_str_wl:
          experiments:
            pass-experiment:
              variables:
                n_nodes: 1
              success_criteria:
              - name: test_success
                mode: string
                match: 'SUCCESS'
  software:
    packages: {}
    environments: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        with open(config_path, "w+", encoding="utf-8") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", global_args=["-w", workspace_name])
        ramble_on(global_args=["-w", workspace_name])
        workspace("analyze", "-f", "text", "json", "yaml", global_args=["-w", workspace_name])

        for ext in ["txt", "json", "yaml"]:
            assert os.path.exists(os.path.join(ws.results_dir, f"results.latest.{ext}"))

        with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
            data = f.read()
            assert "Success criteria summary:" in data
            assert (
                "application::success-criteria-conflicts::_application_function = PASSED" in data
            )
            assert "config::experiment::test_success = PASSED" in data


def test_success_criteria_mutex_versions(mock_applications, workspace_name):
    """
    Tests that same named success_criteria defined in mutually exclusive
    when clauses are handled appropriately.
    """
    test_config = """
ramble:
  variables:
    processes_per_node: '1'
    n_threads: '1'
  applications:
    success-criteria-conflicts@1.0.0:
      workloads:
        version_wl:
          experiments:
            pass-experiment:
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        with open(config_path, "w+", encoding="utf-8") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", global_args=["-w", workspace_name])
        ramble_on(global_args=["-w", workspace_name])
        workspace("analyze", "-f", "text", "json", "yaml", global_args=["-w", workspace_name])

        for ext in ["txt", "json", "yaml"]:
            assert os.path.exists(os.path.join(ws.results_dir, f"results.latest.{ext}"))

        with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
            data = f.read()
            assert "Success criteria summary:" in data
            assert (
                "application::success-criteria-conflicts::_application_function = PASSED" in data
            )
            assert "application::success-criteria-conflicts::test_version = PASSED" in data


def test_success_criteria_multiple_satisfies(mock_applications, workspace_name):
    """
    Tests that an object, Application in this case, defining the same named
    success_criteria in multiple satisfying when conditions, will error out.
    """
    test_config = """
ramble:
  variables:
    processes_per_node: '1'
    n_threads: '1'
  applications:
    success-criteria-conflicts:
      variants:
        force_pass: True
      workloads:
        success_str_wl:
          experiments:
            pass-experiment:
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        with open(config_path, "w+", encoding="utf-8") as f:
            f.write(test_config)
        ws._re_read()

        from ramble.error import RambleCommandError

        expected_err = (
            r"Success criteria '.*' in object '.*' is defined "
            r"multiple times under conflicting satisfied 'when' conditions"
        )

        with pytest.raises(RambleCommandError, match=expected_err):
            workspace("setup", global_args=["-w", workspace_name])


def test_success_criteria_inheritance(mock_applications, workspace_name):
    """
    Tests that same named success_criteria defined in multiple objects (using
    inheritance) is handled appropriately.
    """
    test_config = """
ramble:
  variables:
    processes_per_node: '1'
    n_threads: '1'
  applications:
    success-criteria-conflicts:
      workloads:
        inheritance_wl:
          experiments:
            pass-experiment:
              variables:
                n_nodes: 1
  software:
    packages: {}
    environments: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        with open(config_path, "w+", encoding="utf-8") as f:
            f.write(test_config)
        ws._re_read()

        workspace("setup", global_args=["-w", workspace_name])
        ramble_on(global_args=["-w", workspace_name])
        workspace("analyze", "-f", "text", "json", "yaml", global_args=["-w", workspace_name])

        for ext in ["txt", "json", "yaml"]:
            assert os.path.exists(os.path.join(ws.results_dir, f"results.latest.{ext}"))

        with open(os.path.join(ws.results_dir, "results.latest.txt"), encoding="utf-8") as f:
            data = f.read()
            assert "Success criteria summary:" in data
            assert (
                "application::success-criteria-conflicts::_application_function = PASSED" in data
            )
            assert "application::success-criteria-conflicts::test_inheritance = PASSED" in data
