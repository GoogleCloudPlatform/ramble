# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from __future__ import print_function

import llnl.util.tty.color as color

import ramble.repository

header_color = '@*b'
plain_format = '@.'


def setup_info_parser(subparser, object_type):
    obj_def = ramble.repository.type_definitions[object_type]
    subparser.add_argument(f'{obj_def["singular"]}', help=f'{obj_def["singular"]} name')


def section_title(s):
    return header_color + s + plain_format


def print_text_info(obj):
    obj._verbosity = 'long'
    color.cprint(str(obj))


def print_info(args, object_type):
    obj_def = ramble.repository.type_definitions[object_type]
    obj_name = getattr(args, obj_def['singular'])
    obj = ramble.repository.get(obj_name, object_type=object_type)
    print_text_info(obj)
