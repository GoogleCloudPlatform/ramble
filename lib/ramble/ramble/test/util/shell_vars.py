# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.util.shell_vars import last_pid_var

import pytest


@pytest.mark.parametrize(
    "var_func,shell,expect",
    [
        (last_pid_var, "fish", "$last_pid"),
        (last_pid_var, "bash", "$!"),
        (last_pid_var, "unknown_shell", "$!"),
    ],
)
def test_shell_vars(var_func, shell, expect):
    assert var_func(shell) == expect
