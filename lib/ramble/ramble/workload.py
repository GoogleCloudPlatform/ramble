# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from typing import List
import copy

import ramble.util.colors as rucolor


class WorkloadVariable:
    """Class representing a variable definition"""

    def __init__(
        self,
        name: str,
        default=None,
        description: str = None,
        values=None,
        expandable: bool = True,
        track_used: bool = True,
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
        """
        self.name = name
        self.default = default
        self.description = description
        self.values = values.copy() if isinstance(values, list) else [values]
        self.expandable = expandable
        self.track_used = track_used

    def __str__(self):
        if not hasattr(self, "_str_indent"):
            self._str_indent = 0
        return self.as_str(n_indent=self._str_indent)

    def as_str(self, n_indent: int = 0):
        """String representation of this variable

        Args:
          n_indent (int): Number of spaces to indent string lines with

        Returns:
            (str): Representation of this variable
        """
        indentation = " " * n_indent

        print_attrs = ["Description", "Default", "Values"]

        out_str = rucolor.nested_2(f"{indentation}{self.name}:\n")
        for print_attr in print_attrs:
            name = print_attr
            if print_attr == "Values":
                name = "Suggested Values"
            attr_name = print_attr.lower()

            attr_val = getattr(self, attr_name, None)
            if attr_val:
                out_str += f'{indentation}    {name}: {str(attr_val).replace("@", "@@")}\n'
        return out_str

    def copy(self):
        return copy.deepcopy(self)


class WorkloadEnvironmentVariable:
    """Class representing an environment variable in a workload"""

    def __init__(self, name: str, value=None, description: str = None):
        """WorkloadEnvironmentVariable constructor

        Args:
            name (str): Name of environment variable
            value: Value to set environment variable to
            description (str): Description of the environment variable
        """
        self.name = name
        self.value = value
        self.description = description

    def as_str(self, n_indent: int = 0):
        """String representation of environment variable

        Args:
            n_indent (int): Number of spaces to indent string representation by

        Returns:
            (str): String representing this environment variable
        """
        indentation = " " * n_indent

        print_attrs = ["Description", "Value"]

        out_str = rucolor.nested_2(f"{indentation}{self.name}:\n")
        for name in print_attrs:
            attr_name = name.lower()
            attr_val = getattr(self, attr_name, None)
            if attr_val:
                out_str += f'{indentation}    {name}: {attr_val.replace("@", "@@")}\n'
        return out_str

    def copy(self):
        return copy.deepcopy(self)


class Workload:
    """Class representing a single workload"""

    def __init__(
        self, name: str, executables: List[str], inputs: List[str] = [], tags: List[str] = []
    ):
        """Constructor for a workload

        Args:
            name (str): Name of this workload
            executables (list(str)): List of executable names for this workload
            inputs (list(str)): List of input names for this workload
            tags (list(str)): List of tags for this workload
        """
        self.name = name
        self.variables = {}
        self.environment_variables = {}

        attr_names = ["executables", "inputs", "tags"]
        attr_vals = [executables, inputs, tags]

        for attr, vals in zip(attr_names, attr_vals):
            if isinstance(vals, list):
                setattr(self, attr, vals.copy())
            else:
                attr_val = []
                if vals:
                    attr_val.append(vals)
                setattr(self, attr, attr_val)

    def __str__(self):
        if not hasattr(self, "_str_indent"):
            self._str_indent = 0
        return self.as_str(n_indent=self._str_indent)

    def as_str(self, n_indent: int = 0):
        """String representation of this workload

        Args:
            n_indent (int): Number of spaces to indent string with

        Returns:
            (str): Representation of this workload
        """
        attrs = [("Executables", "executables"), ("Inputs", "inputs"), ("Tags", "tags")]

        indentation = " " * n_indent

        out_str = rucolor.section_title(f"{indentation}Workload: ")
        out_str += f"{self.name}\n"
        for attr in attrs:
            out_str += rucolor.nested_1(f"{indentation}    {attr[0]}: ")
            attr_val = getattr(self, attr[1], [])
            out_str += f"{attr_val}\n"

        if self.variables:
            out_str += rucolor.nested_1(f"{indentation}    Variables:\n")
            for name, var in self.variables.items():
                out_str += var.as_str(n_indent + 4)

        if self.environment_variables:
            out_str += rucolor.nested_1(f"{indentation}    Environment Variables:\n")
            for name, env_var in self.environment_variables.items():
                out_str += env_var.as_str(n_indent + 4)

        return out_str

    def add_variable(self, variable: WorkloadVariable):
        """Add a variable to this workload

        Args:
            variable (WorkloadVariable): New variable to add to this workload
        """
        self.variables[variable.name] = variable

    def add_environment_variable(self, env_var: WorkloadEnvironmentVariable):
        """Add an environment variable to this workload

        Args:
            env_var (WorkloadEnvironmentVariable): New environment variable to add to this workload
        """
        self.environment_variables[env_var.name] = env_var

    def add_executable(self, executable: str):
        """Add an executable to this workload

        Args:
            executable (str): Name of executable to add to this workload
        """
        self.executables.append(executable)

    def add_input(self, input: str):
        """Add an input to this workload

        Args:
            input (str): Name of input to add to this workload
        """
        self.inputs.append(input)

    def add_tag(self, tag: str):
        """Add a tag to this workload

        Args:
            tag (str): Tag to add to this workload
        """
        self.tags.append(tag)

    def is_valid(self):
        """Test if this workload is considered valid

        Returns:
            (bool): True if workload is valid, False otherwise
        """
        if len(self.executables) == 0:
            return False

        return True

    def find_executable(self, exec_name: str):
        """Find an executable in this workload

        Args:
            exec_name (str): Name of executable to find

        Returns:
            (str / None): Name of executable if it exists, None if it is not found
        """
        for executable in self.executables:
            if executable == exec_name:
                return executable
        return None

    def find_input(self, input_name):
        """Find an input in this workload

        Args:
            input_name (str): Name of input to find

        Returns:
            (str / None): Name of input if it exists, None if it is not found
        """
        for input in self.inputs:
            if input == input_name:
                return input
        return None

    def find_variable(self, name):
        """Find a variable in this workload

        Args:
            var_name (str): Name of variable to find

        Returns:
            (WorkloadVariable / None): Variable instance if it exists, None if it is not found
        """
        if name in self.variables:
            return self.variables[name]
        else:
            return None

    def find_environment_variable(self, name):
        """Find an environment variable in this workload

        Args:
            env_var_name (str): Name of environment variable to find

        Returns:
            (WorkloadEnvironmentVariable / None): Environment variable instance
                                                  if it exists, None if it is not found
        """
        if name in self.environment_variables:
            return self.environment_variables[name]
        else:
            return None
