# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class PrecedenceTest(BasicModifier):
    """Modifier to test cross-pass variable precedence logic"""

    name = "precedence-test"

    variant("trigger", default=False, description="Trigger variant")

    modifier_variable(
        name="dep_var",
        default="trigger",
        description="Dependent var",
        mode="test_mode",
    )

    # Generic block
    with when("trigger=True"):
        modifier_variable(
            name="override_var",
            default="generic",
            description="Fallback",
            mode="test_mode",
        )

    # Specific block
    with when("{dep_var}=True"):
        modifier_variable(
            name="override_var",
            default="specific",
            description="Override",
            mode="test_mode",
        )

    mode("test_mode", description="A test mode")

    executable_modifier("test_exec_modifier")

    def test_exec_modifier(self, exec_name, executable, app_inst=None):
        import ramble.util.executable

        prepend_execs = []
        append_execs = [
            ramble.util.executable.CommandExecutable(
                name="test_exec",
                template="echo '{override_var}'",
                redirect=None,
                output_capture=None,
            )
        ]
        return prepend_execs, append_execs
