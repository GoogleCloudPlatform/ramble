# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_mock_workspace_path", "config", "mutable_mock_apps_repo"
)


@pytest.fixture()
def workspace_deactivate():
    yield
    ramble.workspace._active_workspace = None
    os.environ.pop("RAMBLE_WORKSPACE", None)


def test_re_read(tmpdir):
    with tmpdir.as_cwd():
        test_workspace = ramble.workspace.Workspace(os.getcwd(), True)
        test_workspace.clear()
        test_workspace._re_read()
