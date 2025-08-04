# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.error import RambleCommandError
from ramble.main import RambleCommand
from ramble.util.logger import logger


def test_missing_command():
    with pytest.raises(RambleCommandError) as err_info:
        RambleCommand("missing-command")

    assert "does not exist" in str(err_info.value)


def test_available_command():
    import ramble.cmd

    for command in ramble.cmd.all_commands():
        logger.msg(f"Command = {command}")

        RambleCommand(command)


def test_command_output(tmpdir):
    command = RambleCommand("commands")

    formats = ["subcommands", "rst", "names", "bash"]
    for f in formats:
        file = os.path.join(tmpdir, f"outfile.{f}")
        command("--format", f, "--update", file)
        assert os.path.isfile(file)

    target = os.path.join(tmpdir, "outfile.names")
    header = os.path.join(tmpdir, "outfile.subcommands")
    command("--update", target, "--header", header, "-a")
