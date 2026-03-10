# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
import re
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


class SummaryFoms(Enum):
    SUMMARY = "Experiment Summary"
    N_TOTAL = "n_total_repeats"
    N_SUCCESS = "n_success_repeats"


# Try to import the internal parser for the re module
try:
    # See https://github.com/python/cpython/issues/91308
    import re._parser as sre_parse
except ImportError:
    try:
        # This is for Python 3.10 or earlier
        import sre_parse
    except ImportError:
        sre_parse = None


def get_literal_from_regex(regex_str: str) -> str:
    """
    Extracts a first-encountered required literal string from a regex pattern.

    This is used to create fast string pre-filters to avoid executing complex regex matching.
    This is not exhaustive, as it doesn't recurse into sub-patterns. It is only intended as a
    heuristic to short-circuit the matching process.
    """
    if not sre_parse:
        return ""

    try:
        tree = sre_parse.parse(regex_str)
    # re.error is renamed, but it's kept around for backward compatibility
    # See https://docs.python.org/3/library/re.html#exceptions
    except re.error:
        return ""

    current_literal = ""
    for node in tree:
        node_name = str(node[0])
        if node_name == "LITERAL":
            current_literal += chr(node[1])
        elif current_literal:
            break

    return current_literal.strip()
