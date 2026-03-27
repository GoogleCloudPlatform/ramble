# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import csv
import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")
on_cmd = RambleCommand("on")


def test_tables_output(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    ws.write()
    global_args = ["-w", workspace_name]

    _CONFIG = """ramble:
  applications:
    hostname:
      workloads:
        local:
          variables:
            foo: bar
          tables:
          - name: test_table
            columns:
            - name: "hostname"
              figure_of_merit: "possible hostname"
            - name: "foo"
              expression: "{foo}"
          experiments:
            generated:
              variables:
                n_ranks: 1
                n_nodes: 1
    """

    with open(os.path.join(ws.config_dir, "ramble.yaml"), "w") as f:
        f.write(_CONFIG)

    ws._re_read()

    workspace("setup", global_args=global_args)

    on_cmd(global_args=global_args)

    workspace("analyze", global_args=global_args)

    table_path = os.path.join(ws.tables_dir, "test_table.latest.csv")
    assert os.path.exists(table_path)

    with open(table_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        row = rows[0]
        assert "hostname" in row
        assert row["foo"] == "bar"


def test_default_tables_output(workspace_name):
    ws = ramble.workspace.create(workspace_name)
    ws.write()
    global_args = ["-w", workspace_name]

    _CONFIG = """ramble:
  applications:
    hostname:
      workloads:
        local:
          variables:
            foo: bar
          experiments:
            generated:
              variables:
                n_ranks: 1
                n_nodes: 1
    """

    with open(os.path.join(ws.config_dir, "ramble.yaml"), "w") as f:
        f.write(_CONFIG)

    ws._re_read()

    workspace("setup", global_args=global_args)

    on_cmd(global_args=global_args)

    workspace("analyze", global_args=global_args)

    table_path = os.path.join(ws.tables_dir, "generated.latest.csv")
    assert os.path.exists(table_path)

    with open(table_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        row = rows[0]
        assert "application_name" in row
        assert "workload_name" in row
        assert "experiment_name" in row
        # In hostname, there's a figure of merit "possible hostname"
        assert "possible hostname" in row

