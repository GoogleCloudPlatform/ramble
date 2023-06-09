# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.cmd.common.info
import ramble.repository


description = 'get detailed information on a particular application'
section = 'basic'
level = 'short'

app_type = ramble.repository.ObjectTypes.applications


def setup_parser(subparser):
    ramble.cmd.common.info.setup_info_parser(subparser, app_type)


def info(parser, args):
    ramble.cmd.common.info.print_info(args, app_type)
