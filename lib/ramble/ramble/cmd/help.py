# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import sys
from llnl.util.tty.color import colorize

description = "get help on ramble and its commands"
section = "help"
level = "short"

#
# These are longer guides on particular aspects of RAmble. Currently there
# is only one on spec syntax.
#
spec_guide = """\
spec expression syntax:

  application [constraint]

  application                       any application from 'ramble list'

  constraints:
    workloads:
      @B{+workload}                      enable <workload>

  examples:
      hostname               the hostname application and all of its workloads
      hostname +basic        the hostname application and its basic workload
"""


guides = {
    'spec': spec_guide,
}


def setup_parser(subparser):
    help_cmd_group = subparser.add_mutually_exclusive_group()
    help_cmd_group.add_argument('help_command', nargs='?', default=None,
                                help='command to get help on')

    help_all_group = subparser.add_mutually_exclusive_group()
    help_all_group.add_argument(
        '-a', '--all', action='store_const', const='long', default='short',
        help='list all available commands and options')

    help_spec_group = subparser.add_mutually_exclusive_group()
    help_spec_group.add_argument(
        '--spec', action='store_const', dest='guide', const='spec',
        default=None, help='help on the package specification syntax')


def help(parser, args):
    if args.guide:
        print(colorize(guides[args.guide]))
        return 0

    if args.help_command:
        parser.add_command(args.help_command)
        parser.parse_args([args.help_command, '-h'])
    else:
        sys.stdout.write(parser.format_help(level=args.all))
