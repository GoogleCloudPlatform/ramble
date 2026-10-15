# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.platkit import *


class UserManaged(PlatformBase):
    """Platform representing a user managed compute node.

    This platform is used when the user wants to manually specify all
    aspects of their compute node in the workspace configuration.
    """

    name = "user-managed"

    variant(
        "validate_platform",
        default=False,
        description="Whether to validate the platform configuration",
    )
