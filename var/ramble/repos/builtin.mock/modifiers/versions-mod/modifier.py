# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class VersionsMod(BasicModifier):
    name = "versions-mod"

    mode("standard", "Standard execution mode")
    mode("test", "Test mode")
    default_mode("standard")

    version("2.0", "versionsmod 2.0", preferred=True)
    version("1.0", "versionsmod 1.0", preferred=False)

    with when("modifier_version@1.0"):
        environment_variable(
            "MOD_ENV_VAR",
            value="MOD_ENV_VAR_SET_1.0",
            description="Test environment variable",
        )

    with when("@2.0"):
        environment_variable(
            "MOD_ENV_VAR",
            value="MOD_ENV_VAR_SET_2.0",
            description="Test environment variable",
        )
