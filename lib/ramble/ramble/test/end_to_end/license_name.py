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

pytestmark = pytest.mark.usefixtures(
    "mutable_config", "mutable_mock_workspace_path", "mutable_mock_apps_repo"
)

workspace = RambleCommand("workspace")

test_val = "test_val"


def license_param_core(app_name, workspace_name, test_licenses, expected_val):
    test_config = f"""
ramble:
  variables:
    mpi_command: mpirun -n 1
    batch_submit: ''
    processes_per_node: 1
  applications:
    {app_name}:
      workloads:
        template_wl:
          experiments:
            test:
              variables:
                n_ranks: '1'
  software:
    packages: {{}}
    environments: {{}}
"""

    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)
    with open(config_path, "w+", encoding="utf-8") as f:
        f.write(test_config)

    license_path = os.path.join(ws.config_dir, "licenses.yaml")
    with open(license_path, "w+", encoding="utf-8") as f:
        f.write(test_licenses)

    ws._re_read()

    workspace("setup", "--dry-run", global_args=["-w", workspace_name])

    license_inc_path = os.path.join(ws.root, "shared", "licenses", app_name, "license.inc")
    with open(license_inc_path, encoding="utf-8") as f:
        data = f.read()
        # Test the license is added to the include file
        assert expected_val in data


def test_license_name_parent(mutable_mock_apps_repo, workspace_name):
    app_name = "basic-inherited-nolicense"
    test_licenses = f"""
licenses:
  basic:
    set:
      TEST_VAR: {test_val}
"""
    expected_val = test_val
    license_param_core(app_name, workspace_name, test_licenses, expected_val)


def test_license_name_self_implicit(mutable_mock_apps_repo, workspace_name):
    app_name = "basic-inherited-nolicense"
    expected_val = test_val + "_imp"
    test_licenses = f"""
licenses:
  basic:
    set:
      TEST_VAR: {test_val}
  basic-inherited-nolicense:
    set:
      TEST_VAR: {expected_val}
"""
    license_param_core(app_name, workspace_name, test_licenses, expected_val)


def test_license_name_self_explicit(mutable_mock_apps_repo, workspace_name):
    app_name = "basic-inherited"
    expected_val = test_val + "_exp"
    test_licenses = f"""
licenses:
  basic:
    set:
      TEST_VAR: {test_val}
  basic-inherited:
    set:
      TEST_VAR: {expected_val}
"""
    license_param_core(app_name, workspace_name, test_licenses, expected_val)
