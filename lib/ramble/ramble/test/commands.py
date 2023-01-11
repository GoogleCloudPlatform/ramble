# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import llnl.util.tty as tty

from ramble.main import RambleCommand, RambleCommandError


def test_missing_command():
    with pytest.raises(RambleCommandError) as err_info:
        RambleCommand('missing-command')

    assert 'does not exist' in str(err_info.value)


def test_available_command():
    import ramble.cmd

    for command in ramble.cmd.all_commands():
        tty.msg('Command = %s' % command)

        RambleCommand(command)
