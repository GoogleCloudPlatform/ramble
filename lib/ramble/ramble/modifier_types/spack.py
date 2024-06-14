# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble
import deprecation

from ramble.modifier import ModifierBase


class SpackModifier(ModifierBase):
    """Specialized class for modifiers that use spack.

    This class can be used to set up a modifier that uses spack to install
    software for the modifier to work.
    """

    modifier_class = "SpackModifier"

    @deprecation.deprecated(
        deprecated_in="0.5.0",
        removed_in="0.6.0",
        current_version=str(ramble.ramble_version),
        details="The SpackModifier class is deprecated. "
        + "Convert instances to BasicModifier instead",
    )
    def __init__(self, file_path):
        super().__init__(file_path)
