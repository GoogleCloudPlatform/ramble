# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
from typing import Any, Dict, List, Optional, Set

import ramble.util.colors as color


class Variable:
    """Class representing a variable definition"""

    def __init__(
        self,
        name: str,
        default=None,
        description: Optional[str] = None,
        values=None,
        expandable: bool = True,
        track_used: bool = True,
        when=None,
        **kwargs,
    ):
        """Constructor for a new variable

        Args:
            name (str): Name of variable
            default: Default value of variable
            description (str): Description of variable
            values: List of suggested values for variable
            expandable (bool): True if variable can be expanded, False otherwise
            track_used (bool): True if variable should be considered used,
                               False to ignore it for vectorizing experiments
            when (list | None): List of when conditions to apply to directive
        """
        self.name = name
        self.default = default
        self.description = description
        self.values = values.copy() if isinstance(values, list) else [values]
        self.expandable = expandable
        self.track_used = track_used
        self.when = when.copy() if when else []

    def __str__(self):
        if not hasattr(self, "_str_indent"):
            self._str_indent = 0
        return self.as_str(n_indent=self._str_indent)

    def as_str(self, n_indent: int = 0, verbose: bool = False):
        """String representation of this variable

        Args:
          n_indent (int): Number of spaces to indent string lines with

        Returns:
            (str): Representation of this variable
        """
        indentation = " " * n_indent

        if verbose:
            print_attrs = ["Description", "Default", "Values"]

            out_str = color.title_color(f"{indentation}{self.name}:\n", n_indent)
            for print_attr in print_attrs:
                name = print_attr
                if print_attr == "Values":
                    name = "Suggested Values"
                attr_name = print_attr.lower()

                attr_val = getattr(self, attr_name, None)
                if attr_val:
                    out_str += (
                        f"{indentation}    {color.title_color(name, n_indent=n_indent + 4)}: "
                        f"{attr_val!s}\n"
                    )
        else:
            out_str = f"{indentation}{self.name}"

        return out_str

    def copy(self):
        return copy.deepcopy(self)


class VariableModification:
    """Class representing a variable modification"""

    def __init__(
        self,
        name: str,
        modification: str,
        method: str = "set",
        separator: str = " ",
        when=None,
        **kwargs,
    ):
        """Constructor for a new variable modification

        Args:
            name (str): The variable to modify
            modification (str): The value to modify 'name' with
            method (str): How the modification should be applied
            mode (str): Single mode to group this modification into
            modes (str): List of modes to group this modification into
            separator (str): Optional separator to use when modifying with 'append' or
                            'prepend' methods.
            when (list | None): List of when conditions this modification should apply in

        Supported values are 'append', 'prepend', and 'set':
            'append' will add the modification to the end of 'name'
            'prepend' will add the modification to the beginning of 'name'
            'set' (Default) will overwrite 'name' with the modification
        """
        self.name = name
        self.modification = modification
        self.method = method
        self.separator = separator
        self.when = when.copy() if when else []

    def __str__(self):
        if not hasattr(self, "_str_indent"):
            self._str_indent = 0
        return self.as_str(n_indent=self._str_indent)

    def as_str(self, n_indent: int = 0, verbose: bool = False):
        """String representation of this variable

        Args:
          n_indent (int): Number of spaces to indent string lines with

        Returns:
            (str): Representation of this variable
        """
        indentation = " " * n_indent

        print_attrs = ["Modification", "Method", "Separator", "When"]

        out_str = color.title_color(f"{indentation}{self.name}:\n", n_indent)
        for print_attr in print_attrs:
            name = print_attr
            attr_name = print_attr.lower()

            attr_val = getattr(self, attr_name, None)
            if attr_val:
                if print_attr == "Separator":
                    attr_val = f"'{attr_val}'"
                out_str += (
                    f"{indentation}    {color.title_color(name, n_indent=n_indent + 4)}: "
                    f"{attr_val!s}\n"
                )
        return out_str

    def copy(self):
        return copy.deepcopy(self)


class EnvironmentVariable:
    """Class representing an environment variable"""

    def __init__(
        self,
        name: str,
        value=None,
        description: Optional[str] = None,
        method: str = "set",
        append_separator: str = ",",
        when=None,
        **kwargs,
    ):
        """EnvironmentVariable constructor

        Args:
            name (str): Name of environment variable
            value: Value to set environment variable to
            description (str): Description of the environment variable
            method (str): Method to use when defining the env-var.
                          Can be "set", "append", or "prepend"
            append_separator (str): Separator to use when method is "append", otherwise ignored.
            when (list | None): List of when conditions to apply to directive
        """
        self.name = name
        self.value = value
        self.description = description
        self.method = method
        self.separator = append_separator
        self.when = when.copy() if when else []

    def __str__(self):
        if not hasattr(self, "_str_indent"):
            self._str_indent = 0
        return self.as_str(n_indent=self._str_indent)

    def as_str(self, n_indent: int = 0, verbose: bool = False):
        """String representation of environment variable

        Args:
            n_indent (int): Number of spaces to indent string representation by

        Returns:
            (str): String representing this environment variable
        """
        indentation = " " * n_indent

        if verbose:
            print_attrs = ["Description", "Value", "Method"]
            if self.method == "append":
                print_attrs.append("Separator")
            out_str = color.title_color(f"{indentation}{self.name}:\n", n_indent)
            for name in print_attrs:
                attr_name = name.lower()
                attr_val = getattr(self, attr_name, None)
                if attr_val:
                    out_str += (
                        f"{indentation}    {color.title_color(name, n_indent=n_indent + 4)}: "
                        f"{attr_val!s}\n"
                    )
        else:
            out_str = f"{indentation}{self.name}"

        return out_str

    def copy(self):
        return copy.deepcopy(self)


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
        self.set: Dict[str, str] = {}
        self.unset: Set[str] = set()
        self.prepend: List[Dict[str, Dict[str, str]]] = []
        self.append: List[Dict[str, Any]] = []

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
            out_str = color.title_color(f"{indentation}{self.name}:\n", n_indent)
            for method in self.all_methods:
                if getattr(self, method):
                    if n > 0:
                        out_str += "\n"
                    out_str += (
                        f"{indentation}    "
                        f"{color.title_color('method', n_indent=n_indent + 4)}: {method}\n"
                    )
                    n += 1
                    if method == "set":
                        out_str += (
                            f"{indentation}    "
                            f"{color.title_color('modification', n_indent=n_indent + 4)}: "
                            f"{self.set[self.name]}\n"
                        )
                    elif method in ["prepend", "append"]:
                        for method_dict in getattr(self, method):
                            for attr, val in method_dict.items():
                                out_str += (
                                    f"{indentation}    "
                                    f"{color.title_color(attr, n_indent=n_indent + 4)}: {val}\n"
                                )
                    if self.when:
                        out_str += (
                            f"{indentation}    "
                            f"{color.title_color('when', n_indent=n_indent + 4)}: {self.when}\n"
                        )
        else:
            out_str = f"{indentation}{self.name}"

        return out_str

    def copy(self):
        return copy.deepcopy(self)

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
