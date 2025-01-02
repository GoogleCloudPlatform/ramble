# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.main import RambleCommand, RambleCommandError
from ramble.util.logger import logger  # noqa:  F401


def test_missing_command():
    with pytest.raises(RambleCommandError) as err_info:
        RambleCommand("missing-command")

    assert "does not exist" in str(err_info.value)


def test_available_command():
    import ramble.cmd

    for command in ramble.cmd.all_commands():
        logger.msg(f"Command = {command}")

        RambleCommand(command)
