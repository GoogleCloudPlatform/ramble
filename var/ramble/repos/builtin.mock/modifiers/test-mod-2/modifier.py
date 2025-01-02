# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


class TestMod2(BasicModifier):
    """Define a test modifier

    This modifier contains a variable modification that can be layered on top of
    the modifications defined in test-mod
    """

    name = "test-mod-2"

    tags("test")

    mode("test", description="This is a test mode")
    default_mode("test")

    variable_modification(
        "test_var_mod",
        "test-mod-2-append",
        method="append",
        modes=["test"],
    )
