# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import builtins

import ramble.paths
import ramble.util.colors as color
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
        f"`{cmd}` requires ramble's shell support.",
        "",
        "To set up shell support, run the command below for your shell.",
        "",
        color.colorize("@*c{For bash/zsh/sh:}"),
        f"  . {ramble.paths.share_path}/setup-env.sh",
        "",
        color.colorize("@*c{For csh/tcsh:}"),
        f"  source {ramble.paths.share_path}/setup-env.csh",
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


def sanitize_arg_name(base_name: str) -> str:
    """Format argument/command names by converting hyphens to underscores."""
    return base_name.replace("-", "_")


def setup_subcommands_from_prefix(
    subparser,
    dest: str,
    subcommands: builtins.list,
    prefix: str,
    globals_dict: dict,
    subcommand_functions: dict,
    inject_dry_run: bool = False,
):
    """Set up subparsers and map functions for a prefixed list of subcommands.

    Args:
        subparser: Parent ArgumentParser or subparser
        dest (str): Destination attribute name for selected subcommand
        subcommands (list): List of subcommand names or (name, *aliases) tuples
        prefix (str): Prefix used in function names (e.g. 'workspace', 'data', 'deployment')
        globals_dict (dict): The globals() dictionary of the calling module
        subcommand_functions (dict): Dictionary mapping command/alias name -> function
        inject_dry_run (bool): Whether to automatically add --dry-run to subparsers if not present
    """
    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest=dest)

    for cmd_entry in subcommands:
        if isinstance(cmd_entry, (builtins.list, builtins.tuple)):
            name, aliases = cmd_entry[0], builtins.list(cmd_entry[1:])
        else:
            name = cmd_entry
            aliases = []

        # add commands to subcommands dict
        function_name = sanitize_arg_name(f"{prefix}_{name}")
        function = globals_dict[function_name]
        for alias in [name] + aliases:
            subcommand_functions[alias] = function

        # make a subparser and run the command's setup function on it
        setup_parser_cmd_name = sanitize_arg_name(f"{prefix}_{name}_setup_parser")
        setup_parser_cmd = globals_dict[setup_parser_cmd_name]

        subsubparser = sp.add_parser(
            name,
            aliases=aliases,
            help=setup_parser_cmd.__doc__,
            description=setup_parser_cmd.__doc__,
        )
        setup_parser_cmd(subsubparser)

        if inject_dry_run and "--dry-run" not in subsubparser._option_string_actions:
            subsubparser.add_argument(
                "--dry-run",
                dest="dry_run",
                action="store_true",
                help=f"perform a dry run of the {name} command",
            )
