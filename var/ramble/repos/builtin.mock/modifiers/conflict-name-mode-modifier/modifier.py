# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class ConflictNameModeModifier(BasicModifier):

    name = "conflict-name-mode-modifier"

    mode("standard", description="Standard modifier mode")

    default_mode("standard")

    modifier_conflict("name_mode")
