# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from __future__ import print_function

import llnl.util.tty.color as color

import ramble.cmd.common.arguments as arguments
import ramble.repository
import ramble.spec


description = 'get detailed information on a particular application'
section = 'basic'
level = 'short'

header_color = '@*b'
plain_format = '@.'


def padder(str_list, extra=0):
    """Return a function to pad elements of a list."""
    length = max(len(str(s)) for s in str_list) + extra

    def pad(string):
        string = str(string)
        padding = max(0, length - len(string))
        return string + (padding * ' ')
    return pad


def setup_parser(subparser):
    arguments.add_common_arguments(subparser, ['application'])


def section_title(s):
    return header_color + s + plain_format


def print_text_info(app):
    """Print out a plain text description of a application."""

    app._verbosity = 'long'
    color.cprint(str(app))


def info(parser, args):
    app = ramble.repository.get(args.application)
    print_text_info(app)
