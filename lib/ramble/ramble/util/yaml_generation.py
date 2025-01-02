# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Module representing utility functions for managing YAML configuration files
within application definition files

These functions are intended to help read, write, and manipulate YAML based
configuration files that an experiment might use as input.

Workload variables that represent configuration files should be defined using a
'.' delimiter between YAML object names. As an example:

```
foo:
    bar:
        baz: 1.0
```

Would translate to `foo.bar.baz = 1.0` in Ramble syntax.

"""

from typing import Dict, Any
import ruamel.yaml as yaml
import spack.util.spack_yaml as syaml

from ramble.util.logger import logger


def read_config_file(conf_path: str):
    """Read an existing YAML file and return its data as a dictionary

    Args:
        conf_path (str): Path to input configuration file to read

    Returns:
        (dict): Dictionary representation of the data contained in conf_path
    """
    with open(conf_path) as base_conf:
        logger.debug(f"Reading config from {conf_path}")
        try:
            config_dict = syaml.load(base_conf)
        except yaml.YAMLError:
            logger.die(f"YAML Error: Failed to load data from {conf_path}")

    return config_dict


def all_config_options(config_data: Dict):
    """Extract all config options from config_data dictionary

    Args:
        config_data (dict): A config dictionary representing data read from a YAML file.

    Returns:
        (set): Set containing all detected fully qualified option names
    """

    all_configs = set()
    option_parts = []
    for top_level in config_data:
        option_parts.append((top_level, config_data[top_level]))

    while option_parts:
        cur_part = option_parts.pop(0)

        if isinstance(cur_part[1], dict):
            for level in cur_part[1]:
                option_parts.insert(0, (f"{cur_part[0]}.{level}", cur_part[1][level]))
        else:
            if len(cur_part[0].split(".")) > 1:
                all_configs.add(cur_part[0])

    return all_configs


def get_config_value(config_data: Dict, option_name: str):
    """Get a config option based on dictionary attribute syntax

    Given an option_name of the format: attr1.attr2.attr3 return its value
    from config_data.

    Args:
        config_data (dict): A config dictionary representing data read from a YAML file.
        option_name (str): Name of config option to get

    Returns:
        (Any): Value of config option
    """
    option_parts = option_name.split(".")

    option_scope = config_data

    while len(option_parts) > 1:
        cur_part = option_parts.pop(0)
        if cur_part in option_scope:
            option_scope = option_scope[cur_part]
        else:
            return None

    if option_parts[0] in option_scope:
        return option_scope[option_parts[0]]
    return None


def set_config_value(config_data: Dict, option_name: str, option_value: Any, force: bool = False):
    """Set a config option based on dictionary attribute syntax

    Given an option_name of the format: attr1.attr2.attr3 set its value to
    option_value in config_data.

    Args:
        config_data (dict): A config dictionary representing data read from a YAML file.
        option_name (str): Name of config option to set
        option_value (any): Value to set config option to
        force (bool): If true, all missing layers in the attribute list are created.
                      If false, only sets existing attributes
    """
    option_parts = option_name.split(".")

    option_scope = config_data

    while len(option_parts) > 1:
        cur_part = option_parts.pop(0)
        if cur_part not in option_scope:
            if not force:
                return
            option_scope[cur_part] = {}
        option_scope = option_scope[cur_part]

    set_value = force or option_parts[0] in option_scope
    if set_value:
        option_scope[option_parts[0]] = option_value


def remove_config_value(config_data: Dict, option_name: str):
    """Remove a config option based on dictionary attribute syntax

    Given an option_name of the format: attr1.attr2.attr3 remote it from config_data.
    Also, remove any parent scopes that are empty.

    Args:
        config_data (dict): A config dictionary representing data read from a YAML file.
        option_name (str): Name of config option to set
    """
    option_parts = option_name.split(".")

    option_scope = config_data

    reverse_stack = []

    # Walk the parts, to find the lowest level to remove
    while len(option_parts) > 1:
        cur_part = option_parts.pop(0)
        if cur_part not in option_scope:
            return
        reverse_stack.append((option_scope, cur_part))
        option_scope = option_scope[cur_part]

    # Remove the lowest level
    if option_parts[0] in option_scope:
        del option_scope[option_parts[0]]

    # Walk back up the stack, and remove any empty parents
    while reverse_stack:
        option_scope, cur_part = reverse_stack.pop()
        if cur_part in option_scope and not option_scope[cur_part]:
            del option_scope[cur_part]


def apply_default_config_values(config_data, app_inst, default_config_string):
    """Apply default config values (from config_data) to an experiment

    Process all workloads variables (for the current workload in app_inst). Any
    variable who's expanded value is equal to default_config_string will have
    its value overwritten to the value in the config_dict dictionary.

    Args:
        config_data (dict): Dictionary of config data read from a YAML file
        app_inst (application): Application instance representing an experiment
        default_config_string (str): String that conveys the default config_data
                                     should be used in place of the current value.
    """
    workload = app_inst.workloads[app_inst.expander.workload_name]

    # Set all '{default_config_value}' values to value from the base config
    for var_name, var_def in workload.variables.items():
        if len(var_name.split(".")) > 1:
            var_val = app_inst.expander.expand_var(app_inst.expander.expansion_str(var_name))

            if var_val == default_config_string:
                var_val = get_config_value(config_data, var_name)

                app_inst.define_variable(var_name, var_val)
