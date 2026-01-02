# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.util.colors as rucolor


class PackageManagerRequirement:
    """Class representing a package manager requirement for a modifier"""

    def __init__(
        self, command: str, validation_type: str, regex: str, package_manager: str, when: list
    ):
        """Constructor for PackageManagerRequirement object
        Args:
            command: Package manager command to execute, when evaluating the requirement
            validation_type: Type of validation to perform on output of command
            regex: Regular expression to use when validation_type is either 'contains_regex'
                   or 'does_no_contain_regex'
            package_manager: Name of the package manager this requirement should apply to
            when: List of when conditions this requirement should apply to
        """
        self.name = command  # In order to print correctly from info, all obj need 'name'
        self.command = command
        self.validation_type = validation_type
        self.regex = regex
        self.package_manager = package_manager
        self.when = when

    def __str__(self):
        if not hasattr(self, "_str_indent"):
            self._str_indent = 0
        return self.as_str(n_indent=self._str_indent)

    def as_str(self, n_indent: int = 0, verbose: bool = False):
        """String representation of this requirement

        Args:
            n_indent: Number of spaces to indent string lines with
            verbose: Print verbose output

        Returns:
            (str): Representation of this requirement
        """
        indentation = " " * n_indent

        if verbose:
            print_attrs = ["command", "validation_type", "package_manager", "regex"]

            out_str = f"{indentation}{rucolor.section_title('When:')} {self.when}\n"
            for print_attr in print_attrs:
                attr_val = getattr(self, print_attr, None)

                if attr_val:
                    out_str += (
                        f"{indentation}    {rucolor.nested_1(print_attr)}: "
                        f'{str(attr_val).replace("@", "@@")}\n'
                    )
        else:
            out_str = f"{indentation}{self.when}"

        return out_str
