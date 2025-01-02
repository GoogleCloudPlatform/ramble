# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.cmd.common.info
import ramble.repository


description = "get detailed information on a particular object"
section = "basic"
level = "short"


def setup_parser(subparser):
    ramble.cmd.common.info.setup_info_parser(subparser)


def info(parser, args):
    ramble.cmd.common.info.print_info(args)
