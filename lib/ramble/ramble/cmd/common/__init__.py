# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import llnl.util.tty.color as color

import ramble.paths
from ramble.util.logger import logger


def shell_init_instructions(cmd, equivalent):
    """Print out instructions for users to initialize shell support.

    Arguments:
        cmd (str): the command the user tried to run that requires
            shell support in order to work
        equivalent (str): a command they can run instead, without
            enabling shell support
    """

    shell_specific = "{sh_arg}" in equivalent

    msg = [
        "`%s` requires ramble's shell support." % cmd,
        "",
        "To set up shell support, run the command below for your shell.",
        "",
        color.colorize("@*c{For bash/zsh/sh:}"),
        "  . %s/setup-env.sh" % ramble.paths.share_path,
        "",
        color.colorize("@*c{For csh/tcsh:}"),
        "  source %s/setup-env.csh" % ramble.paths.share_path,
        "",
        "Or, if you do not want to use shell support, run "
        + ("one of these" if shell_specific else "this")
        + " instead:",
        "",
    ]

    if shell_specific:
        msg += [
            equivalent.format(sh_arg="--sh  ") + "  # bash/zsh/sh",
            equivalent.format(sh_arg="--csh ") + "  # csh/tcsh",
        ]
    else:
        msg += ["  " + equivalent]

    msg += [""]
    logger.error(*msg)
