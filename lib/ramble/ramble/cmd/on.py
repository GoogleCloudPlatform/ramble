# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import sys

import ramble.workspace
import ramble.expander

if sys.version_info >= (3, 3):
    from collections.abc import Sequence  # novm noqa: F401
else:
    from collections import Sequence  # noqa: F401


description = "And now's the time, the time is now"
section = 'secret'
level = 'long'


def setup_parser(subparser):
    subparser.add_argument(
        '-w', '--workspace', metavar='workspace', dest='ramble_workspace',
        help='name of workspace to `ramble on`',
             required=False)


def ramble_on(args):
    ws = ramble.cmd.require_active_workspace(cmd_name='workspace info')

    with ws.write_transaction():
        ws.run_experiments()


def on(parser, args):
    """Look for a function called environment_<name> and call it."""
    ramble_on(args)
