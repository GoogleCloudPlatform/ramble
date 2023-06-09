# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.modifier import ModifierBase


class SpackModifier(ModifierBase):
    """Specialized class for modifiers that use spack.

    This class can be used to set up a modifier that uses spack to install
    software for the modifier to work.
    """

    modifier_class = 'SpackModifier'
    uses_spack = True

    def __init__(self, file_path):
        super().__init__(file_path)
