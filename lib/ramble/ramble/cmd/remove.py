# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import llnl.util.tty as tty

import ramble.cmd
import ramble.cmd.common.arguments as arguments
import ramble.workspace


description = 'remove a spec from a workspace'
section = "workspaces"
level = "long"


def setup_parser(subparser):
    subparser.add_argument('-l', '--list-name',
                           dest='list_name', default='specs',
                           help="name of the list to add specs to")
    arguments.add_common_arguments(subparser, ['yes_to_all', 'specs'])


def remove(parser, args):
    workspace = ramble.cmd.require_active_workspace(cmd_name='remove')

    for spec in ramble.cmd.parse_specs(args.specs):
        if not workspace.remove(spec):
            tty.msg("Workload {0} was missing from {1}"
                    .format(spec.name, workspace.name))
        else:
            tty.msg('Removing %s from workspace %s' %
                    (spec, workspace.name))
    workspace.write()
