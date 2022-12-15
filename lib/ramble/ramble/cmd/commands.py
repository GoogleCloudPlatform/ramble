# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from __future__ import print_function

import argparse
import copy
import os
import re
import sys

import llnl.util.filesystem as fs
import llnl.util.tty as tty
from llnl.util.argparsewriter import (
    ArgparseWriter, ArgparseRstWriter, ArgparseCompletionWriter
)
from llnl.util.tty.colify import colify

import ramble.cmd
import ramble.main
import ramble.paths
from ramble.main import section_descriptions


description = "list available ramble commands"
section = "developer"
level = "long"


#: list of command formatters
formatters = {}


#: standard arguments for updating completion scripts
#: we iterate through these when called with --update-completion
update_completion_args = {
    "bash":  {
        "aliases": True,
        "format": "bash",
        "header": os.path.join(
            ramble.paths.share_path, "bash", "ramble-completion.in"),
        "update": os.path.join(
            ramble.paths.share_path, "ramble-completion.bash"),
    },
}


def formatter(func):
    """Decorator used to register formatters"""
    formatters[func.__name__] = func
    return func


def setup_parser(subparser):
    subparser.add_argument(
        "--update-completion", action='store_true', default=False,
        help="regenerate ramble's tab completion scripts")

    subparser.add_argument(
        '-a', '--aliases', action='store_true', default=False,
        help='include command aliases')
    subparser.add_argument(
        '--format', default='names', choices=formatters,
        help='format to be used to print the output (default: names)')
    subparser.add_argument(
        '--header', metavar='FILE', default=None, action='store',
        help='prepend contents of FILE to the output (useful for rst format)')
    subparser.add_argument(
        '--update', metavar='FILE', default=None, action='store',
        help='write output to the specified file, if any command is newer')
    subparser.add_argument(
        'rst_files', nargs=argparse.REMAINDER,
        help='list of rst files to search for `_cmd-ramble-<cmd>` cross-refs')


class RambleArgparseRstWriter(ArgparseRstWriter):
    """RST writer tailored for ramble documentation."""

    def __init__(self, prog, out=None, aliases=False,
                 documented_commands=[],
                 rst_levels=['-', '-', '^', '~', ':', '`']):
        out = sys.stdout if out is None else out
        super(RambleArgparseRstWriter, self).__init__(
            prog, out, aliases, rst_levels)
        self.documented = documented_commands

    def usage(self, *args):
        string = super(RambleArgparseRstWriter, self).usage(*args)

        cmd = self.parser.prog.replace(' ', '-')
        if cmd in self.documented:
            string += '\n:ref:`More documentation <cmd-{0}>`\n'.format(cmd)

        return string


class SubcommandWriter(ArgparseWriter):
    def format(self, cmd):
        return '    ' * self.level + cmd.prog + '\n'


_positional_to_subroutine = {
    'application': '_all_applications',
    'spec': '_all_applications',
    'filter': '_all_applications',
    'section': '_config_sections',
    'workspace': '_workspaces',
    'keys': '_keys',
    'help_command': '_subcommands',
    'namespace': '_repos',
    'pytest': '_tests',
}


class BashCompletionWriter(ArgparseCompletionWriter):
    """Write argparse output as bash programmable tab completion."""

    def body(self, positionals, optionals, subcommands):
        if positionals:
            return """
    if $list_options
    then
        {0}
    else
        {1}
    fi
""".format(self.optionals(optionals), self.positionals(positionals))
        elif subcommands:
            return """
    if $list_options
    then
        {0}
    else
        {1}
    fi
""".format(self.optionals(optionals), self.subcommands(subcommands))
        else:
            return """
    {0}
""".format(self.optionals(optionals))

    def positionals(self, positionals):
        # If match found, return function name
        for positional in positionals:
            for key, value in _positional_to_subroutine.items():
                if positional.startswith(key):
                    return value

        # If no matches found, return empty list
        return 'RAMBLE=""'

    def optionals(self, optionals):
        return 'RAMBLE_COMPREPLY="{0}"'.format(' '.join(optionals))

    def subcommands(self, subcommands):
        return 'RAMBLE_COMPREPLY="{0}"'.format(' '.join(subcommands))


@formatter
def subcommands(args, out):
    parser = ramble.main.make_argument_parser()
    ramble.main.add_all_commands(parser)
    writer = SubcommandWriter(parser.prog, out, args.aliases)
    writer.write(parser)


def rst_index(out):
    out.write('\n')

    index = ramble.main.index_commands()
    sections = index['long']

    dmax = max(len(section_descriptions.get(s, s)) for s in sections) + 2
    cmax = max(len(c) for _, c in sections.items()) + 60

    row = "%s  %s\n" % ('=' * dmax, '=' * cmax)
    line = '%%-%ds  %%s\n' % dmax

    out.write(row)
    out.write(line % (" Category ", " Commands "))
    out.write(row)
    for section, commands in sorted(sections.items()):
        description = section_descriptions.get(section, section)

        for i, cmd in enumerate(sorted(commands)):
            description = description.capitalize() if i == 0 else ''
            ref = ':ref:`%s <ramble-%s>`' % (cmd, cmd)
            comma = ',' if i != len(commands) - 1 else ''
            bar = '| ' if i % 8 == 0 else '  '
            out.write(line % (description, bar + ref + comma))
    out.write(row)


@formatter
def rst(args, out):
    # create a parser with all commands
    parser = ramble.main.make_argument_parser()
    ramble.main.add_all_commands(parser)

    # extract cross-refs of the form `_cmd-ramble-<cmd>:` from rst files
    documented_commands = set()
    for filename in args.rst_files:
        with open(filename) as f:
            for line in f:
                match = re.match(r'\.\. _cmd-(ramble-.*):', line)
                if match:
                    documented_commands.add(match.group(1).strip())

    # print an index to each command
    rst_index(out)
    out.write('\n')

    # print sections for each command and subcommand
    writer = RambleArgparseRstWriter(
        parser.prog, out, args.aliases, documented_commands)
    writer.write(parser)


@formatter
def names(args, out):
    commands = copy.copy(ramble.cmd.all_commands())

    if args.aliases:
        commands.extend(ramble.main.aliases.keys())

    colify(commands, output=out)


@formatter
def bash(args, out):
    parser = ramble.main.make_argument_parser()
    ramble.main.add_all_commands(parser)

    writer = BashCompletionWriter(parser.prog, out, args.aliases)
    writer.write(parser)


def prepend_header(args, out):
    if not args.header:
        return

    with open(args.header) as header:
        out.write(header.read())


def _commands(parser, args):
    """This is the 'regular' command, which can be called multiple times.

    See ``commands()`` below for ``--update-completion`` handling.
    """
    formatter = formatters[args.format]

    # check header first so we don't open out files unnecessarily
    if args.header and not os.path.exists(args.header):
        tty.die("No such file: '%s'" % args.header)

    # if we're updating an existing file, only write output if a command
    # or the header is newer than the file.
    if args.update:
        if os.path.exists(args.update):
            files = [
                # pyc -> py
                ramble.cmd.get_module(command).__file__.rstrip('c')
                for command in ramble.cmd.all_commands()]
            if args.header:
                files.append(args.header)
            last_update = os.path.getmtime(args.update)
            if not any(os.path.getmtime(f) > last_update for f in files):
                tty.msg('File is up to date: %s' % args.update)
                return

        tty.msg('Updating file: %s' % args.update)
        with open(args.update, 'w') as f:
            prepend_header(args, f)
            formatter(args, f)

        if args.update_completion:
            fs.set_executable(args.update)

    else:
        prepend_header(args, sys.stdout)
        formatter(args, sys.stdout)


def update_completion(parser, args):
    """Iterate through the shells and update the standard completion files.

    This is a convenience method to avoid calling this command many
    times, and to simplify completion update for developers.

    """
    for shell, shell_args in update_completion_args.items():
        for attr, value in shell_args.items():
            setattr(args, attr, value)
        _commands(parser, args)


def commands(parser, args):
    if args.update_completion:
        if args.format != 'names' or any([
                args.aliases, args.update, args.header
        ]):
            tty.die("--update-completion can only be specified alone.")

        # this runs the command multiple times with different arguments
        return update_completion(parser, args)

    else:
        # run commands normally
        return _commands(parser, args)
