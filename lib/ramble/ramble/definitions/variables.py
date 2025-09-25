# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from typing import List, Optional

import ramble.util.colors as rucolor


def _title_color(title: str, n_indent: int = 0):
    """Set the appropriate color for titles based on indentation"""
    if n_indent == 0:
        out_str = rucolor.section_title(f"{title}")
    elif n_indent == 4:
        out_str = rucolor.nested_1(f"{title}")
    elif n_indent == 8:
        out_str = rucolor.nested_2(f"{title}")
    elif n_indent == 12:
        out_str = rucolor.nested_3(f"{title}")
    elif n_indent == 16:
        out_str = rucolor.nested_4(f"{title}")

    return out_str


class EnvironmentVariableModifications:
    """Class representing modifications of an environment variable"""

    all_methods = ["set", "unset", "prepend", "append"]

    def __init__(
        self,
        name: str,
        modification: str,
        method: str = "set",
        when: Optional[List[str]] = None,
        **kwargs,
    ):
        """Constructor for environment variable modification

        Args:
            name (str): The name of the environment variable that will be modified
            modification (str): The value of the modification
            method (str): The method of the modification.
            mode (str | None): Name of mode this env_var_modification should apply in
            modes (list(str) | None): List of mode names this env_var_modification should apply in
            when (list | None): List of when conditions this env_var_modification should apply in

        Supported values for method are:

            - set: Defines the variable to equal the modification value
            - unset: Removes any definition of the variable from the environment
            - prepend: Prepends the modification to the beginning of the variable.
            Always uses the separator ':'
            - append: Appends the modification value to the end of the value. Allows a
            keyword argument of 'separator' to define the delimiter between values.
        """
        self.name = name
        self.when = when.copy() if when else []
        self.set = {}
        self.unset = {}
        self.prepend = []
        self.append = []

        self.add_modification(
            modification=modification,
            method=method,
            **kwargs,
        )

    def __str__(self):
        if not hasattr(self, "_str_indent"):
            self._str_indent = 0
        return self.as_str(n_indent=self._str_indent)

    def as_str(self, n_indent: int = 0, verbose: bool = False):
        """String representation of this environment variable modification

        Args:
          n_indent (int): Number of spaces to indent string lines with

        Returns:
            (str): Representation of this environment variable modification
        """
        indentation = " " * n_indent

        if verbose:
            n = 0
            out_str = _title_color(f"{indentation}{self.name}:\n", n_indent)
            for method in self.all_methods:
                if getattr(self, method):
                    if n > 0:
                        out_str += "\n"
                    out_str += (
                        f"{indentation}    {_title_color('method', n_indent=n_indent + 4)}: "
                        f"{method}\n"
                    )
                    n += 1
                    if method == "set":
                        out_str += (
                            f"{indentation}    "
                            f"{_title_color('modification', n_indent=n_indent + 4)}: "
                            f"{self.set[self.name]}\n"
                        )
                    elif method in ["prepend", "append"]:
                        for method_dict in getattr(self, method):
                            for attr, val in method_dict.items():
                                out_str += (
                                    f"{indentation}    "
                                    f"{_title_color(attr, n_indent=n_indent + 4)}: {val}\n"
                                )
                    if self.when:
                        out_str += (
                            f"{indentation}    {_title_color('when', n_indent=n_indent + 4)}: "
                            f"{self.when}\n"
                        )
        else:
            out_str = f"{indentation}{self.name}"

        return out_str

    def add_modification(
        self,
        modification: str,
        method: str = "set",
        **kwargs,
    ):
        """Adds a modification to this environment variable

        Args:
            modification (str): The value of the modification
            method (str): The method of the modification.
            separator (str): The separator to use when appending or prepending
            when (list | None): List of when conditions this env_var_modification should apply in
        """
        if method == "set":
            self.set = {self.name: modification}
        elif method == "unset":
            self.unset = {self.name}
        elif method == "prepend":
            prepend_dict = {
                "paths": {self.name: modification},
            }
            self.prepend.append(prepend_dict)
        elif method == "append":
            append_dict = {}
            separator = kwargs.get("separator", ":")
            if separator != ":":
                append_dict = {
                    "vars": {self.name: modification},
                    "var-separator": separator,
                }
            else:
                append_dict = {
                    "paths": {self.name: modification},
                }
            self.append.append(append_dict)
