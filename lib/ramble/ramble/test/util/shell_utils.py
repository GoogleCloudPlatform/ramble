# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.util.shell_utils import (
    last_pid_var,
    source_str,
    get_compatible_base_shell,
    cmd_sub_str,
    UnsupportedError,
)

import pytest


@pytest.mark.parametrize(
    "var_func,shell,expect",
    [
        (last_pid_var, "fish", "$last_pid"),
        (last_pid_var, "bash", "$!"),
        (last_pid_var, "unknown_shell", "$!"),
        (source_str, "bash", "."),
        (source_str, "csh", "source"),
        (source_str, "unknown_shell", ""),
        (get_compatible_base_shell, "bash", "sh"),
        (get_compatible_base_shell, "sh", "sh"),
    ],
)
def test_shell_specializations(var_func, shell, expect):
    assert var_func(shell) == expect


def test_cmd_sub_str():
    with pytest.raises(UnsupportedError):
        cmd_sub_str("bat", "VER")

    assert cmd_sub_str("fish", "uname -n") == "(uname -n)"
    assert cmd_sub_str("bash", "uname -n") == "`uname -n`"
