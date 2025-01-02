# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Utils for handling shell specialization"""

from ramble.error import RambleError

_SUPPORTED_BASE_SHELLS = frozenset(["sh", "fish", "csh", "bat"])


def last_pid_var(shell: str) -> str:
    if shell == "fish":
        # Based on https://fishshell.com/docs/current/fish_for_bash_users.html#special-variables
        last_pid_var = "$last_pid"
    else:
        # This works for sh/bash and (t)csh
        last_pid_var = "$!"
    return last_pid_var


_shell_source_map = {"sh": ".", "bash": ".", "fish": "source", "csh": "source", "bat": "."}


def source_str(shell):
    """Wrapper to return the `source` command for a given shell

    Args:
        shell (str): Name of shell to get the source command for

    Returns:
        (str): Source command for the requested shell.
    """

    if shell in _shell_source_map:
        return _shell_source_map[shell]
    return ""


_base_shell_map = {"bash": "sh", "tcsh": "csh"}


def get_compatible_base_shell(shell):
    """Get the compatible base shell

    For instance, given bash it returns sh. This is commonly used to translate
    shell name for calling spack utils, which only support such "base" shells.

    Args:
        shell (str): Name of shell

    Returns:
        (str): The base compatible shell.
    """
    return _base_shell_map.get(shell, shell)


def cmd_sub_str(shell, cmd: str):
    """Get the command substitution string of the given shell"""
    base_shell = get_compatible_base_shell(shell)
    if base_shell not in _SUPPORTED_BASE_SHELLS or base_shell == "bat":
        raise UnsupportedError(f"Command substitution is not supported in {shell} shell")
    if shell == "fish":
        return f"({cmd})"
    return f"`{cmd}`"


class UnsupportedError(RambleError):
    """Error when certain shell features are not supported."""
