# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class UnsetEnvVarMod(BasicModifier):
    """Define a modifier with only an environment variable modification using
    the unset method"""

    name = "unset-env-var-mod"

    tags("test")

    mode("test", description="This is a test mode")

    env_var_modification("test_var", method="unset", mode="test")
