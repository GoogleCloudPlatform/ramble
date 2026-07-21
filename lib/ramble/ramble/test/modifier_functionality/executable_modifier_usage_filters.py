# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import re

import pytest

import ramble.workspace
from ramble.error import RambleCommandError
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "filter_type,expected_count",
    [
        ("none", -1),
        ("once", 1),
        ("all_mpi", 6),
        ("first_mpi", 1),
    ],
)
def test_executable_modifier_usage_filters(
    mutable_mock_workspace_path,
    mutable_applications,
    mock_modifiers,
    workspace_name,
    filter_type,
    expected_count,
):

    global_args = ["-w", workspace_name]

    pre_str = f"exec_mod_{filter_type}_pre_applied"
    post_str = f"exec_mod_{filter_type}_post_applied"

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        workspace(
            "manage",
            "experiments",
            "openfoam",
            "--wf",
            "motorbike_20m",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "openfoam_path=/not/needed",
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        workspace(
            "manage",
            "modifiers",
            "--add",
            "--scope",
            "workspace",
            "--name",
            "exec-mod-usage-filters",
            global_args=global_args,
        )

        with open(os.path.join(ws.config_dir, "variants.yaml"), "w+", encoding="utf-8") as f:
            f.write(f"""variants:
  usage_filter_type: {filter_type}""")

        ws._re_read()

        workspace("setup", "--dry-run", global_args=global_args)

        exec_path = os.path.join(
            ws.experiment_dir, "openfoam", "motorbike_20m", "generated", "execute_experiment"
        )

        assert os.path.isfile(exec_path)

        pre_regex = re.compile(pre_str)
        post_regex = re.compile(post_str)

        with open(exec_path, encoding="utf-8") as f:
            pre_count = 0
            post_count = 0

            for line in f:
                pre_m = pre_regex.search(line)
                if pre_m:
                    pre_count += 1

                post_m = post_regex.search(line)
                if post_m:
                    post_count += 1

        if expected_count >= 0:
            assert pre_count == expected_count
            assert post_count == expected_count
        else:
            assert pre_count > 0
            assert post_count > 0


def test_executable_modifier_usage_filters_broken_errors(
    mutable_mock_workspace_path,
    mutable_applications,
    mock_modifiers,
    workspace_name,
):

    expected_err = (
        "When extracting a usage_filter for an executable_modifier "
        "on modifier exec-mod-usage-filters the filter __broken__ does not exist"
    )
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        workspace(
            "manage",
            "experiments",
            "openfoam",
            "--wf",
            "motorbike_20m",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "openfoam_path=/not/needed",
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        workspace(
            "manage",
            "modifiers",
            "--add",
            "--scope",
            "workspace",
            "--name",
            "exec-mod-usage-filters",
            global_args=global_args,
        )

        with open(os.path.join(ws.config_dir, "variants.yaml"), "w+", encoding="utf-8") as f:
            f.write("""variants:
  usage_filter_type: broken""")

        ws._re_read()

        with pytest.raises(RambleCommandError, match=expected_err):
            workspace("setup", "--dry-run", global_args=global_args)
