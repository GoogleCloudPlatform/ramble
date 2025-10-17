# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from enum import Enum


class MODIFIER_CONFLICT(Enum):
    # Conflict on identical name only
    name_only = 0

    # Conflict on name, and mode
    name_mode = 1

    # Conflict on name, and overlapping executables
    name_executables = 2

    # Conflict on name, mode, and overlapping executables
    name_mode_executables = 3
    name_executables_mode = 3
