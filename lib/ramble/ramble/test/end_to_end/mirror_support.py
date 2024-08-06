# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand, RambleCommandError

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

workspace = RambleCommand("workspace")


def assert_text_in_mirror_log(ws, text):
    mirror_log = os.path.join(ws.log_dir, "mirror.latest.out")
    with open(mirror_log) as f:
        content = f.read()
        assert text in content


@pytest.mark.parametrize(
    "pkgman,expect_error, extra_args",
    [
        ("null", False, []),
        ("spack", False, []),
        ("pip", True, []),
        ("eessi", True, []),
        # Allowed when phases are explicitly specified
        (
            "pip",
            False,
            ["--phases", "mirror_inputs", "--include-phase-dependencies"],
        ),
    ],
)
def test_mirror_support(pkgman, expect_error, extra_args, tmpdir):
    test_config = f"""
ramble:
  variants:
    package_manager: {pkgman}
  variables:
    mpi_command: ''
    batch_submit: '{{execute_experiment}}'
    processes_per_node: 1
    n_ranks: 1
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test: {{}}
  software:
    packages: {{}}
    environments: {{}}
"""
    ws_name = f"test_{pkgman}_mirror_support"
    ws = ramble.workspace.create(ws_name)
    ramble.workspace.activate(ws)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, "w+") as f:
        f.write(test_config)

    ws._re_read()

    mirror_path = os.path.join(tmpdir, ws_name)
    if expect_error:
        with pytest.raises(RambleCommandError):
            workspace("mirror", "--dry-run", "-d", mirror_path, *extra_args)
        assert_text_in_mirror_log(ws, f"{pkgman} does not support mirroring")
    else:
        workspace("mirror", "--dry-run", "-d", mirror_path, *extra_args)
        assert_text_in_mirror_log(ws, "Successfully created software")
