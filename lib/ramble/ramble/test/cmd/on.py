# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
import ramble.test.cmd.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    'mutable_mock_workspace_path', 'config', 'mutable_mock_repo')

workspace = RambleCommand('workspace')
add = RambleCommand('add')
remove = RambleCommand('remove')
on = RambleCommand('on')


def test_on_command():
    ws_name = 'test'
    workspace('create', ws_name)

    with ramble.workspace.read('test') as ws:
        add('basic')
        ramble.test.cmd.workspace.check_basic(ws)

        workspace('concretize')
        assert ws.is_concretized()

        workspace('setup')
        assert os.path.exists(ws.root + '/all_experiments')

        on()


def test_execute_nothing():
    ws_name = 'test'
    workspace('create', ws_name)
    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        add('basic')
        ramble.test.cmd.workspace.check_basic(ws)

        ws.concretize()
        assert ws.is_concretized()

        ws.run_pipeline('setup')
        assert os.path.exists(ws.root + '/all_experiments')

        ws.run_experiments()
