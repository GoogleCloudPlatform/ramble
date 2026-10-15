# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble
import ramble.main

pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = ramble.main.RambleCommand("workspace")
on = ramble.main.RambleCommand("on")


@pytest.mark.maybeslow
def test_cleanup_directive(mock_applications, workspace_name):
    global_args = ["-w", workspace_name]
    ws = ramble.workspace.create(workspace_name)
    workspace(
        "manage",
        "experiments",
        "cleanup-test",
        "--wf",
        "test",
        "-v",
        "n_nodes=1",
        "-v",
        "processes_per_node=1",
        "-v",
        "batch_submit={execute_experiment}",
        "-v",
        "file_to_check=myfile.txt",
        "--default-variable-value",
        "1",
        global_args=global_args,
    )
    ws._re_read()
    workspace("setup", global_args=global_args)

    run_dir = os.path.join(ws.experiment_dir, "cleanup-test", "test", "generated")

    # Set up two files, with one going to be removed by the pre-cleanup
    pre_file_path = os.path.join(run_dir, "pre-myfile.txt")
    open(pre_file_path, "w", encoding="utf-8")
    post_file_path = os.path.join(run_dir, "post-myfile.txt")
    open(post_file_path, "w", encoding="utf-8")
    assert os.path.exists(pre_file_path)
    assert os.path.exists(post_file_path)

    on()

    # pre_file.txt should be deleted by pre-cleanup
    assert not os.path.exists(pre_file_path)
    assert os.path.exists(post_file_path)

    # file1.txt should exist (created by the app's executable)
    assert os.path.exists(os.path.join(run_dir, "file0.txt"))

    # All *.log should be deleted by post-cleanup
    assert not os.path.exists(os.path.join(run_dir, "file1.log"))
    assert not os.path.exists(os.path.join(run_dir, "subdir", "file2.log"))
