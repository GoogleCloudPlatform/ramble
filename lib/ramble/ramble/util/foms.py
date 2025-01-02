# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
from enum import Enum


# For a FOM, the direction that is 'better' e.g., faster is better
class BetterDirection(Enum):
    HIGHER = 1
    LOWER = 2
    INDETERMINATE = 3  # requires interpretation or FOM type not defined
    INAPPLICABLE = 4  # non-numerical or no direction is 'better', like strings or categories

    @classmethod
    def from_str(cls, string):
        try:
            return cls[string.upper()]
        except KeyError:
            return None


class FomType(Enum):
    TIME = 1
    THROUGHPUT = 2
    MEASURE = 3
    CATEGORY = 4
    INFO = 5
    UNDEFINED = 6

    def better_direction(self):
        direction = {
            FomType.TIME: BetterDirection.LOWER,
            FomType.THROUGHPUT: BetterDirection.HIGHER,
            FomType.MEASURE: BetterDirection.INDETERMINATE,
            FomType.CATEGORY: BetterDirection.INAPPLICABLE,
            FomType.INFO: BetterDirection.INAPPLICABLE,
            FomType.UNDEFINED: BetterDirection.INDETERMINATE,
        }

        return direction[self]

    def copy(self):
        return copy.deepcopy(self)

    @classmethod
    def from_str(cls, string):
        try:
            return cls[string.upper()]
        except KeyError:
            return None

    def to_dict(self):
        """Converts the FomType enum member to a dictionary representation."""
        return {"name": self.name, "better_direction": self.better_direction().name}
