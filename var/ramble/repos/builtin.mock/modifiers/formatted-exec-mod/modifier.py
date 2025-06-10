# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class FormattedExecMod(BasicModifier):
    """Define a modifier for testing formatted executables

    This modifier is just a test of the formatted executable language.
    """

    name = "formatted-exec-mod"

    tags("test")

    mode("test", description="This is a test mode")
    default_mode("test")

    formatted_executable(
        "mod_formatted_exec",
        prefix="FROM_MOD ",
        indentation="4",
        commands=['echo "Test formatted exec"'],
    )
