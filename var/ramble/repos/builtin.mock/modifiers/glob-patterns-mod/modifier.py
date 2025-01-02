# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class GlobPatternsMod(BasicModifier):
    """Define a modifier to test globbing

    This modifier tests globbing in the modifier language.
    """

    name = "glob-patterns-mod"

    tags("test")

    mode("base", description="This is a base mode with no modifications")
    mode(
        "test-glob", description="This test mode turns on mods using globbing"
    )
    default_mode("base")

    variable_modification("var_mod", "{mod_var}", modes=["test*"])

    env_var_modification("env_var_mod", "modded", modes=["test*"])

    modifier_variable(
        "mod_var",
        default="var_mod_modified",
        description="This is a modifier variable",
        modes=["test*"],
    )
