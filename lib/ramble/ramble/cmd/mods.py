# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.repository
import ramble.cmd.common.list
import ramble.cmd.common.info


description = "list and get information on available modifiers"
section = "basic"
level = "short"

subcommands = [["list", "ls"], "info"]

mod_type = ramble.repository.ObjectTypes.modifiers

formatters = {}


def mods_info_setup_parser(subparser):
    """Information about a modifier"""
    ramble.cmd.common.info.setup_info_parser(subparser, mod_type)


def mods_info(args):
    ramble.cmd.common.info.print_info(args, mod_type)


def mods_list_setup_parser(subparser):
    """List available modifiers"""
    ramble.cmd.common.list.setup_list_parser(subparser, mod_type)


def mods_list(args):
    ramble.cmd.common.list.perform_list(args, mod_type)


#: Dictionary mapping subcommand names and aliases to functions
subcommand_functions = {}


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest="mods_command")

    for name in subcommands:
        if isinstance(name, (list, tuple)):
            name, aliases = name[0], name[1:]
        else:
            aliases = []

        # add commands to subcommands dict
        function_name = "mods_%s" % name
        function = globals()[function_name]
        for alias in [name] + aliases:
            subcommand_functions[alias] = function

        # make a subparser and run the command's setup function on it
        setup_parser_cmd_name = "mods_%s_setup_parser" % name
        setup_parser_cmd = globals()[setup_parser_cmd_name]

        subsubparser = sp.add_parser(
            name,
            aliases=aliases,
            help=setup_parser_cmd.__doc__,
            description=setup_parser_cmd.__doc__,
        )
        setup_parser_cmd(subsubparser)


def mods(parser, args):
    """Look for a function called mods_<name> and call it."""
    action = subcommand_functions[args.mods_command]
    action(args)
