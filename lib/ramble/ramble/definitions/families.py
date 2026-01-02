# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from typing import List, Optional


class Families:
    """Class representing object family membership"""

    def __init__(
        self,
        origin_type: str,
        families: Optional[List[str]] = None,
    ):
        """Constructor for families object

        Args:
            origin_type: Base object type
            families: List of families
        """
        self.family_type = f"{origin_type}_family"
        self.families = families if families is not None else []

    def __iter__(self):
        """Iterate over families"""
        yield from self.families

    def __str__(self):
        if not hasattr(self, "_str_indent"):
            self._str_indent = 0
        return self.as_str(n_indent=self._str_indent)

    def as_str(self, n_indent: int = 0, **kwargs):
        """String representation of this object's families

        Args:
            n_indent: Number of spaces to indent string lines with

        Returns:
            (str): Representation of this variable
        """
        indentation = " " * n_indent

        out_str = ""
        for family in self.families:
            out_str += f"{indentation}{self.family_type}={family}\n"

        return out_str

    def add_families(self, families: List[str]):
        """Add new families to this object"""
        updated_families = sorted(set(self.families + families))
        self.families = updated_families
