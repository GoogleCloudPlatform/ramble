# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.syskit import *


class UserManaged(SystemBase):
    """System representing a user managed environment.

    This system is used when the user wants to manually specify all
    aspects of their compute environment in the workspace configuration.
    """

    name = "user-managed"
