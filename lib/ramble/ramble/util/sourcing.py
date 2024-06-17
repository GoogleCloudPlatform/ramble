# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

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
