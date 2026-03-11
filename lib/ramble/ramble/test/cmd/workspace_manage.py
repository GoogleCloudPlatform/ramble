# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures("mutable_mock_workspace_path")


workspace = RambleCommand("workspace")


def test_manage_variable_multiple_equals(workspace_name, tmpdir):
    ws = ramble.workspace.create(workspace_name)

    global_args = ["-w", workspace_name]

    # Highest precedence, experiment scope
    workspace(
        "manage",
        "experiments",
        "gromacs",
        "--wf",
        "water_bare",
        "-v",
        "n_nodes=1",
        "-v",
        "n_ranks=1",
        "-v",
        "test_var=foo=bar",
        "-v",
        "test_list_var=[ val1 = val2, val3=val4]",
        "-v",
        "test_other_var = test1=test2=test3",
        global_args=global_args,
    )

    tests = [
        "test_var: foo=bar",
        "test_list_var:",
        "- val1 = val2",
        "- val3=val4",
        "test_other_var: test1=test2=test3",
    ]

    results = [False for _ in tests]

    with open(ws.config_file_path) as f:
        for line in f:
            for idx, test_str in enumerate(tests):
                if test_str in line:
                    results[idx] = True

    assert all(results)


def test_manage_experiments_no_overwrite_wm_vars(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]
    workspace(
        "manage",
        "experiments",
        "hostname",
        "--wf",
        "parallel",
        "--wm",
        "user-managed",
        global_args=global_args,
    )
    with open(ws.config_file_path) as f:
        content = f.read()
        assert "processes_per_node:" in content
        assert "batch_submit" not in content
        assert "mpi_command" not in content
