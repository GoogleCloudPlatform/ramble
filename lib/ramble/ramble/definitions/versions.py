# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from typing import Optional

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

import ramble.util.colors as rucolor
from ramble.language.language_base import DirectiveError


class ObjectVersion:
    def __init__(
        self,
        version_number: str = "",
        version: Optional[Version] = None,
        description: str = "",
        origin_type: str = "",
        preferred: bool = False,
    ):
        if version:
            self.version = version
        elif version_number:
            try:
                self.version = Version(version_number)
            except InvalidVersion:
                raise DirectiveError(
                    f"Version number '{version_number}' must conform to Python packaging version "
                    "specifier format. Please refer to "
                    "https://packaging.pypa.io/en/latest/version.html for valid formats."
                )
        else:
            raise DirectiveError(
                "An ObjectVersion requires either a Version object or a version number"
            )
        self.description = description
        self.origin_type = origin_type
        self.preferred = preferred

    def copy(self):
        """Construct a copy of self and return it"""
        return ObjectVersion(
            version_number=str(self.version),
            description=self.description,
            origin_type=self.origin_type,
            preferred=self.preferred,
        )

    def apply(self, ver_to_apply):
        # Apply a version on top of the current version
        # This method's logic will depend on how version layering is implemented.
        # For now, it simply returns the ver_to_apply if it's preferred.
        if ver_to_apply.preferred:
            return ver_to_apply
        return self

    def __str__(self):
        return self.get_version_num()

    def as_str(self, n_indent: int = 0, verbose: bool = False):
        """String representation of this version

        Args:
            n_indent (int): Number of spaces to indent string with
            verbose: Print verbose

        Returns:
            (str): Representation of this version
        """
        indentation = " " * n_indent
        out_str = rucolor.section_title(f"{indentation}{str(self.version).replace('@', '@@')}\n")
        out_str += rucolor.nested_1(f"{indentation}    Description: ") + f"{self.description}\n"
        out_str += rucolor.nested_1(f"{indentation}    Preferred: ") + f"{self.preferred}\n"

        return out_str

    def get_version(self):
        """Returns the packaging.version.Version representation of this version"""
        return self.version

    def get_version_num(self):
        """Returns the version number of this version"""
        return str(self.version)

    def evaluate_conflicts(self, variant):
        """Error if this version conflicts with a variant that is used"""
        # This is a placeholder; actual conflict logic will be implemented later.
        pass

    def satisfies(self, variant):
        """Determine if an experiment's variant satisfies this version

        Args:
            variant: A version variant containing the "@" sigil

        Returns:
            (bool): True or False, based if the experiment's variant satisfies
                    the version
        """
        # Convert the variant syntax to a python packaging specifier set
        variant_name, value = variant.split("@")

        satisfied = False
        if value:
            if ":" not in value:
                spec_set = SpecifierSet(f"~={value}", prereleases=True)
            elif value.startswith(":"):
                spec_set = SpecifierSet(f"<={value.split(':')[1]}", prereleases=True)
            elif value.endswith(":"):
                spec_set = SpecifierSet(f">={value.split(':')[0]}", prereleases=True)
            else:
                start, end = value.split(":")
                spec_set = SpecifierSet(f">={start},<={end}", prereleases=True)

            satisfied = spec_set.contains(self.version)

        return satisfied
