# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import pathlib
import shutil

import pytest

import ramble.workspace
from ramble.main import RambleCommand

pytestmark = [
    pytest.mark.maybeslow,
    pytest.mark.usefixtures(
        "mutable_config",
        "mutable_mock_workspace_path",
        "mutable_applications",
        "mutable_modifiers",
        "mutable_package_managers",
        "mutable_workflow_managers",
    ),
]

ws_cmd = RambleCommand("workspace")


def test_setup_analyze(test_case_path, request):
    """test_setup_analyze tests ramble objects that contain a `test_cases` directory.

    Specifically, it assumes the following structure for the `test_cases` directory:

    ```
    test_cases/
    └── test_scenario_1 (can have multiple scenarios)
        ├── artifacts
        │   └── <application-name>__<workload_name>__<experiment_name>
        │       └── <experiment_name>.out (can have other artifacts)
        ├── expected_analyze.out
        └── configs (this is required)
            └── ramble.yaml (can contain more config files)
            └── includes (optional includes dir, when present, add to the include section)
                └── variables.yaml (optional)
    ```

    When writing a Ramble object, if a `test_cases` directory is included, then
    the test case will be run to verify the output of analyze.

    There is an example in the osu-micro-benchmarks application directory.
    """

    def _copy_tree(src_dir_path, dest_dir_path):
        for item in src_dir_path.iterdir():
            dest = dest_dir_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy(item, dest)

    ws_name = request.node.name.replace("[", "_").replace("]", "_")
    global_args = ["-w", ws_name]
    ws = ramble.workspace.create(ws_name)
    ws.write()
    src_config_dir_path = test_case_path / "configs"
    dest_config_path = pathlib.Path(os.path.join(ws.config_dir))
    _copy_tree(src_config_dir_path, dest_config_path)
    dest_includes_dir_path = dest_config_path / "includes"
    if dest_includes_dir_path.is_dir():
        ws_cmd("manage", "includes", "--add", str(dest_includes_dir_path), global_args=global_args)
    ws._re_read()
    # TODO: add assertions around setup artifacts
    ws_cmd("setup", "--dry-run", global_args=global_args)

    # Copy over experiment run artifacts for analyze purpose
    artifacts_dir_path = test_case_path / "artifacts"
    if not artifacts_dir_path.is_dir():
        return
    dest_exp_root_dir = ws.experiment_dir
    for src_child_dir in artifacts_dir_path.iterdir():
        if not src_child_dir.is_dir():
            continue
        child_path_parts = src_child_dir.name.split("__")
        dest_exp_dir_path = pathlib.Path(os.path.join(dest_exp_root_dir, *child_path_parts))
        _copy_tree(src_child_dir, dest_exp_dir_path)
    ws_cmd("analyze", global_args=global_args)
    # Check the analyze output matches with the expected
    actual_analyze = os.path.join(ws.root, "results.latest.txt")
    assert os.path.isfile(actual_analyze)
    expected_analyze = test_case_path / "expected_analyze.out"
    assert expected_analyze.is_file()
    with open(actual_analyze) as f:
        actual_content = f.read().strip()
    with open(str(expected_analyze)) as f:
        expected_content = f.read().strip()
    assert len(expected_content) > 0
    # The actual_content can contain some extra executor output, so only assert
    # the expected output is included.
    assert expected_content in actual_content
