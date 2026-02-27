# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from enum import Enum

import ramble.error
from ramble.util.logger import logger

key_type = Enum("key_type", ["reserved", "optional", "required"])
output_level = Enum("output_level", ["key", "variable"])
default_keys = {
    "workspace_name": {"type": key_type.reserved, "level": output_level.variable},
    "workspace": {"type": key_type.reserved, "level": output_level.variable},
    "workspace_root": {"type": key_type.reserved, "level": output_level.variable},
    "workspace_configs": {"type": key_type.reserved, "level": output_level.variable},
    "workspace_software": {"type": key_type.reserved, "level": output_level.variable},
    "workspace_logs": {"type": key_type.reserved, "level": output_level.variable},
    "workspace_inputs": {"type": key_type.reserved, "level": output_level.variable},
    "workspace_experiments": {"type": key_type.reserved, "level": output_level.variable},
    "workspace_shared": {"type": key_type.reserved, "level": output_level.variable},
    "workspace_archives": {"type": key_type.reserved, "level": output_level.variable},
    "workspace_deployments": {"type": key_type.reserved, "level": output_level.variable},
    "application_name": {"type": key_type.reserved, "level": output_level.key},
    "application_run_dir": {"type": key_type.reserved, "level": output_level.variable},
    "application_input_dir": {"type": key_type.reserved, "level": output_level.variable},
    "application_namespace": {"type": key_type.reserved, "level": output_level.key},
    "application_version": {"type": key_type.reserved, "level": output_level.key},
    "simplified_application_namespace": {"type": key_type.reserved, "level": output_level.key},
    "workload_name": {"type": key_type.reserved, "level": output_level.key},
    "workload_run_dir": {"type": key_type.reserved, "level": output_level.variable},
    "workload_input_dir": {"type": key_type.reserved, "level": output_level.variable},
    "workload_namespace": {"type": key_type.reserved, "level": output_level.key},
    "simplified_workload_namespace": {"type": key_type.reserved, "level": output_level.key},
    "license_input_dir": {"type": key_type.reserved, "level": output_level.variable},
    "experiments_file": {"type": key_type.reserved, "level": output_level.key},
    "experiment_name": {"type": key_type.reserved, "level": output_level.key},
    "experiment_hash": {"type": key_type.reserved, "level": output_level.key},
    "experiment_run_dir": {"type": key_type.reserved, "level": output_level.variable},
    "experiment_status": {"type": key_type.reserved, "level": output_level.key},
    "RAMBLE_STATUS": {"type": key_type.reserved, "level": output_level.key},
    "experiment_index": {"type": key_type.reserved, "level": output_level.variable},
    "experiment_namespace": {"type": key_type.reserved, "level": output_level.key},
    "simplified_experiment_namespace": {"type": key_type.reserved, "level": output_level.key},
    "log_dir": {"type": key_type.reserved, "level": output_level.variable},
    "log_file": {"type": key_type.reserved, "level": output_level.variable},
    "err_file": {"type": key_type.reserved, "level": output_level.variable},
    "env_path": {"type": key_type.reserved, "level": output_level.variable},
    "input_name": {"type": key_type.reserved, "level": output_level.variable},
    "is_repeat_parent": {"type": key_type.reserved, "level": output_level.variable},
    "is_repeat_child": {"type": key_type.reserved, "level": output_level.variable},
    "repeat_index": {"type": key_type.reserved, "level": output_level.variable},
    "spec_name": {"type": key_type.optional, "level": output_level.variable},
    "env_name": {"type": key_type.optional, "level": output_level.variable},
    "n_ranks": {"type": key_type.required, "level": output_level.key},
    "n_nodes": {"type": key_type.required, "level": output_level.key},
    "processes_per_node": {"type": key_type.required, "level": output_level.key},
    "n_threads": {"type": key_type.optional, "level": output_level.key},
    "batch_submit": {"type": key_type.required, "level": output_level.variable},
    "mpi_command": {"type": key_type.required, "level": output_level.variable},
    "workload_template_name": {"type": key_type.reserved, "level": output_level.key},
    "experiment_template_name": {"type": key_type.reserved, "level": output_level.key},
    "unformatted_command": {"type": key_type.reserved, "level": output_level.variable},
    "unformatted_command_without_logs": {
        "type": key_type.reserved,
        "level": output_level.variable,
    },
}


class Keywords:
    """Class to represent known ramble keywords.

    Each keyword contains a dictionary of its attributes. Currently, these include:
    - type
    - level

    Valid types are identified by the 'key_type' variable as an enum.
    Valid levels are identified by the 'output_level'.

    Current key types are:
      - Reserved: Ramble defines these, and a user should not be allowed to define them
      - Optional: Ramble can function with a definition from the user but it isn't required
      - Required: Ramble requires a definition for these. Ramble will try to set sensible defaults,
        but it might not be possible always.

    Current levels are:
      - Key: Ramble defines this as a top level variable. When results are
             output, these are hoisted to a set of variables that are guaranteed to
             be in the output. These are non-application specific inputs that
             define a Ramble experiment.
      - Variable: These are considered standard variables. They might be
                  derived from the values of entries with the level `key`. In results, they
                  are presented in the variables section. These may include application
                  specific inputs to further configure the experiment.
    """

    workspace_name: str
    workspace: str
    workspace_root: str
    workspace_configs: str
    workspace_software: str
    workspace_logs: str
    workspace_inputs: str
    workspace_experiments: str
    workspace_shared: str
    workspace_archives: str
    workspace_deployments: str
    application_name: str
    application_run_dir: str
    application_input_dir: str
    application_namespace: str
    application_version: str
    simplified_application_namespace: str
    workload_name: str
    workload_run_dir: str
    workload_input_dir: str
    workload_namespace: str
    simplified_workload_namespace: str
    license_input_dir: str
    experiments_file: str
    experiment_name: str
    experiment_hash: str
    experiment_run_dir: str
    experiment_status: str
    RAMBLE_STATUS: str
    experiment_index: str
    experiment_namespace: str
    simplified_experiment_namespace: str
    log_dir: str
    log_file: str
    err_file: str
    env_path: str
    input_name: str
    repeat_index: str
    spec_name: str
    env_name: str
    n_ranks: str
    n_nodes: str
    processes_per_node: str
    n_threads: str
    batch_submit: str
    mpi_command: str
    workload_template_name: str
    experiment_template_name: str
    unformatted_command: str
    unformatted_command_without_logs: str

    def __init__(self, extra_keys=None):
        # Merge in additional Keys:
        self.keys = default_keys.copy()
        if extra_keys is None:
            extra_keys = {}
        self.update_keys(extra_keys)

    def copy(self):
        new_inst = type(self)()
        new_inst.keys = self.keys.copy()
        new_inst.update_keys({})
        return new_inst

    def update_keys(self, extra_keys):
        self.keys.update(extra_keys)
        # Define class attributes for all of the keys
        for key in self.keys.keys():
            setattr(self, key, key)

    def is_valid(self, key):
        """Check if a key is valid as a known keyword"""
        return key in self.keys.keys()

    def is_reserved(self, key):
        """Check if a key is reserved"""
        if not self.is_valid(key):
            return False
        return self.keys[key]["type"] == key_type.reserved

    def is_optional(self, key):
        """Check if a key is optional"""
        if not self.is_valid(key):
            return False
        return self.keys[key]["type"] == key_type.optional

    def is_required(self, key):
        """Check if a key is required"""
        if not self.is_valid(key):
            return False
        return self.keys[key]["type"] == key_type.required

    def is_key_level(self, key):
        """Check if key is part of the key level"""
        if not self.is_valid(key):
            return False
        return self.keys[key]["level"] == output_level.key

    def is_variable_level(self, key):
        """Check if key is part of the variable level"""
        if not self.is_valid(key):
            return False
        return self.keys[key]["level"] == output_level.variable

    def all_required_keys(self):
        """Yield all required keys

        Yields:
            (str): Key name
        """
        for key in self.keys.keys():
            if self.is_required(key):
                yield key

    def all_reserved_keys(self):
        """Yield all reserved keys

        Yields:
            (str): Key name
        """
        for key in self.keys.keys():
            if self.is_reserved(key):
                yield key

    def check_reserved_keys(self, definitions):
        """Check a dictionary of variable definitions for reserved keywords"""
        if not definitions:
            return

        for definition in definitions.keys():
            if self.is_reserved(definition):
                raise RambleKeywordError(
                    f'Keyword "{definition}" has been defined, ' + "but is reserved by ramble."
                )

    def check_required_keys(self, definitions, warn_validation=True, die_on_validate_error=True):
        """Check a dictionary of variable definitions for all required keywords"""
        if not definitions:
            return

        required_set = set()
        for key in self.keys.keys():
            if self.is_required(key):
                required_set.add(key)

        for definition in definitions.keys():
            if definition in required_set:
                required_set.remove(definition)

        if len(required_set) > 0:
            if warn_validation:
                for key in required_set:
                    logger.warn(f'Required key "{key}" is not defined')

            if die_on_validate_error:
                raise RambleKeywordError(
                    "One or more required keys " + "are not defined within an experiment."
                )


class RambleKeywordError(ramble.error.RambleError):
    """Superclass for all errors to do with Ramble Keywords"""


keywords = Keywords()
