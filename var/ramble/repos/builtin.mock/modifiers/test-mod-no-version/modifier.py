# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class TestModNoVersion(BasicModifier):
    """Define a test modifier that has no version

    This modifier is just a test of various aspects of the modifier language.
    """

    name = "test-mod-no-version"
    tags("test")
    mode("test", description="This is a test mode")
    default_mode("test")
    modifier_conflict(MODIFIER_CONFLICT.name_mode_executables)

    mode(
        "app-scope", description="This is a test mode at the application scope"
    )

    mode("wl-scope", description="This is a test mode at the workload scope")

    mode(
        "exp-scope", description="This is a test mode at the experiment scope"
    )
