# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.main


pytestmark = pytest.mark.usefixtures("mutable_config", "workspace_deactivate")


def test_unknown_global_argument_is_rejected(capsys):
    ret = ramble.main.main(argv=["--madeuparg", "workspace", "list"])

    captured = capsys.readouterr()
    assert ret == 1
    assert "unrecognized arguments: --madeuparg" in captured.err


def test_command_argument_before_command_is_rejected(capsys):
    ret = ramble.main.main(argv=["--dry-run", "workspace", "list"])

    captured = capsys.readouterr()
    assert ret == 1
    assert "unrecognized arguments: --dry-run" in captured.err

