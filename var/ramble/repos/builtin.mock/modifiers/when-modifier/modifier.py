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
    mode("test", "Test mode")
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

    variant(
        "env_var_modification_active",
        default=False,
        values=[True, False],
        description="Test env var modification",
    )

    with when("+env_var_modification_active"):
        env_var_modification(
            "APP_ENV_VAR",
            modification="APP_ENV_VAR_MODIFIED",
            method="set",
            when="when-modifier_mode=standard",
        )

    variant(
        "exec_modifier_active",
        default=False,
        values=[True, False],
        description="Test exec modifier",
    )

    executable_modifier(
        "test_exec_modifier",
        when=["+exec_modifier_active"],
    )

    def test_exec_modifier(self, exec_name, executable, app_inst=None):
        prepend_execs = []
        append_execs = [
            ramble.util.executable.CommandExecutable(
                name="test_exec_modifier_exec",
                template="echo 'append executable'",
                redirect=None,
                output_capture=None,
            )
        ]

        return prepend_execs, append_execs

    variant(
        "variable_modification_active",
        default=False,
        values=[True, False],
        description="Test variable modifier",
    )

    variable_modification(
        "test_variable",
        modification="test var modified",
        method="set",
        mode="test",
        when=["+variable_modification_active"],
    )
