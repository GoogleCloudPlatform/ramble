# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.main import RambleCommand

# everything here should be mocked if possible
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "workload,experiments,expected_generated,expected_dropped",
    [
        ("always", [("test1", "foo")], ["test1"], []),
        (
            "only_when_var_is_foo",
            [("test_foo", "foo"), ("test_bar", "bar")],
            ["test_foo"],
            ["test_bar"],
        ),
        (
            "exclude_when_var_is_bar",
            [("test_foo", "foo"), ("test_bar", "bar")],
            ["test_foo"],
            ["test_bar"],
        ),
    ],
)
def test_workload_where_clauses(
    workload,
    experiments,
    expected_generated,
    expected_dropped,
    mutable_config,
    mutable_mock_workspace_path,
    mutable_mock_apps_repo,
):
    """Test workload where and exclude_where clauses."""

    import ramble.workspace

    workspace_name = f"test_workload_where_clauses_{workload}"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    for exp, var in experiments:
        workspace(
            "manage",
            "experiments",
            "workload-where-mock",
            "--workload-filter",
            workload,
            "--experiment-name",
            exp,
            "-v",
            f"test_var={var}",
            global_args=["-D", ws.root],
        )

    out = workspace("setup", "--dry-run", global_args=["-D", ws.root])

    for exp in expected_generated:
        assert f"workload-where-mock.{workload}.{exp}" in out

    for exp in expected_dropped:
        assert f"workload-where-mock.{workload}.{exp}" not in out


@pytest.mark.parametrize(
    "workload,experiments,expected_warning",
    [
        (
            "only_when_var_is_foo",
            [("test_bar", "bar"), ("test_baz", "baz")],
            "Workload only_when_var_is_foo generated zero valid experiments because they were "
            "all filtered out by the workload's internal clauses.",
        ),
    ],
)
def test_workload_where_clauses_warnings(
    workload,
    experiments,
    expected_warning,
    mutable_config,
    mutable_mock_workspace_path,
    mutable_mock_apps_repo,
):
    """Test workload where and exclude_where clauses."""

    import ramble.workspace

    workspace_name = f"test_workload_where_clauses_warnings_{workload}"
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    for exp, var in experiments:
        workspace(
            "manage",
            "experiments",
            "workload-where-mock",
            "--workload-filter",
            workload,
            "--experiment-name",
            exp,
            "-v",
            f"test_var={var}",
            global_args=["-D", ws.root],
        )

    out = workspace("setup", "--dry-run", global_args=["-D", ws.root])

    assert expected_warning in out
