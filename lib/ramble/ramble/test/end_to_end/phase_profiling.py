# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "mutable_mock_apps_repo",
    "mutable_mock_mods_repo",
    "workspace_deactivate",
)

workspace = RambleCommand("workspace")


@pytest.mark.maybeslow
def test_workspace_setup_phase_profiling(tmpdir, make_workspace_from_config):
    test_config = """
ramble:
  modifiers:
    - name: test-mod
      mode: test
  variables:
    processes_per_node: 1
    mpi_command: ''
    batch_submit: '{execute_experiment}'
    modeless_required_var: 'dummy'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_exp:
              variables: {}
"""
    _, ws_name = make_workspace_from_config(test_config)

    profile_output = os.path.join(str(tmpdir), "profile_output.txt")

    workspace(
        "setup",
        "--phases",
        "make_experiments",
        "--profile-phase",
        "make_experiments",
        "--profile-phase-output",
        profile_output,
        global_args=["-w", ws_name],
    )

    assert os.path.exists(profile_output)
    with open(profile_output, encoding="utf-8") as f:
        content = f.read()

    # These assertions try to be compatible with older versions of line-profiler,
    # which don't prefix function names with class names in the output.
    assert (
        "Function: ApplicationBase._make_experiments" in content
        or "Function: _make_experiments" in content
    )
    assert (
        "Function: ApplicationBase._define_commands" in content
        or "Function: _define_commands" in content
    )
    assert "Function: TestMod.test_builtin" in content or "Function: test_builtin" in content

    assert (
        "Function: ApplicationBase._mirror_inputs" not in content
        and "Function: _mirror_inputs" not in content
    )
    assert (
        "Function: ApplicationBase.validate_experiment" not in content
        and "Function: validate_experiment" not in content
    )
