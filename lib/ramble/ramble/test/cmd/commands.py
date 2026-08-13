# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from unittest.mock import patch

import pytest

import ramble.cmd
import ramble.config
from ramble.error import RambleCommandError
from ramble.main import RambleCommand
from ramble.util.logger import logger

command = RambleCommand("commands")


def test_missing_command():
    with pytest.raises(RambleCommandError) as err_info:
        RambleCommand("missing-command")

    assert "does not exist" in str(err_info.value)


def test_available_command():
    for cmd in ramble.cmd.all_commands():
        logger.msg(f"Command = {cmd}")
        RambleCommand(cmd)


def test_command_output(tmpdir):
    formats = ["subcommands", "rst", "names", "bash"]
    for f in formats:
        file = os.path.join(tmpdir, f"outfile.{f}")
        command("--format", f, "--update", file)
        assert os.path.isfile(file)

    target = os.path.join(tmpdir, "outfile.names")
    header = os.path.join(tmpdir, "outfile.subcommands")
    command("--update", target, "--header", header, "-a")
    assert os.path.isfile(target)


def test_command_alias_output(mutable_config):
    with ramble.config.override("config:aliases", {"ws": "workspace"}):
        out = command("-a", output=str)
        assert "ws" in out
        assert "workspace" in out


def test_command_invalid_header(tmpdir):
    missing_header = os.path.join(tmpdir, "nonexistent_header.txt")
    out = command("--header", missing_header, fail_on_error=False)
    assert "No such file" in out


def test_command_update_completion_conflict():
    out = command("--update-completion", "-a", fail_on_error=False)
    assert "--update-completion can only be specified alone" in out


def test_command_update_completion(tmpdir):
    bash_no_aliases = str(tmpdir.join("ramble-completion.bash"))
    base_with_aliases = str(tmpdir.join("custom-ramble-completion.bash"))
    mock_args = {
        "bash_no_aliases": {
            "aliases": False,
            "format": "bash",
            "header": os.path.join(ramble.paths.share_path, "bash", "ramble-completion.in"),
            "update": bash_no_aliases,
        },
        "base_with_aliases": {
            "aliases": True,
            "format": "bash",
            "header": os.path.join(ramble.paths.share_path, "bash", "ramble-completion.in"),
            "update": base_with_aliases,
        },
    }
    with patch.dict("ramble.cmd.commands.update_completion_args", mock_args):
        command("--update-completion")
        assert os.path.isfile(bash_no_aliases)
        assert os.path.isfile(base_with_aliases)
