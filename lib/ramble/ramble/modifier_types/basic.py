# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.modifier import ModifierBase


class BasicModifier(ModifierBase):
    """Specialized class for basic modifiers.

    This class can be used to set up a modifier that can be composed into
    experiment definitions.
    """

    modifier_class = "BasicModifier"

    def __init__(self, file_path):
        super().__init__(file_path)
