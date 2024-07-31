# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import llnl.util.tty.color as color

import ramble.cmd.common.arguments as arguments
import ramble.repository

header_color = "@*b"
plain_format = "@."


def setup_info_parser(subparser):
    subparser.add_argument("object", help="Name of object to print info for")

    arguments.add_common_arguments(subparser, ["obj_type"])


def section_title(s):
    return header_color + s + plain_format


def print_text_info(obj):
    obj._verbosity = "long"
    color.cprint(str(obj))


def print_info(args):
    object_type = ramble.repository.ObjectTypes[args.type]
    obj_name = args.object
    obj = ramble.repository.get(obj_name, object_type=object_type)
    print_text_info(obj)
