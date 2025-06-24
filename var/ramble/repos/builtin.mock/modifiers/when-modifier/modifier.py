# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class WhenModifier(BasicModifier):
    name = "when-modifier"

    mode("standard", "Standard execution mode")
    default_mode("standard")

    variant(
        "modifier_included",
        default=False,
        values=[True, False],
        description="Test variant",
    )

    with when("+modifier_included"):
        modifier_variable(
            "mod_var_test",
            mode="standard",
            default="included",
            description="Test variable",
        )

    variant(
        "mod_env_var_included",
        default=False,
        values=[True, False],
        description="Test mod env var",
    )

    with when("+mod_env_var_included"):
        environment_variable(
            "MOD_ENV_VAR",
            value="MOD_ENV_VAR_SET",
            description="Test environment variable",
        )
