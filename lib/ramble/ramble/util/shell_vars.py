# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Utils for getting common shell special variables"""


def last_pid_var(shell: str) -> str:
    if shell == "fish":
        # Based on https://fishshell.com/docs/current/fish_for_bash_users.html#special-variables
        last_pid_var = "$last_pid"
    else:
        # This works for sh/bash and (t)csh
        last_pid_var = "$!"
    return last_pid_var
