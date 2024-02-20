# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.repository
import ramble.cmd.common.list

description = "list and search available applications"
section = "basic"
level = "short"

app_type = ramble.repository.ObjectTypes.applications


def setup_parser(subparser):
    ramble.cmd.common.list.setup_list_parser(subparser,
                                             app_type)


def list(parser, args):
    ramble.cmd.common.list.perform_list(args, app_type)
