# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from enum import Enum

import ramble.error
import ramble.util.logger

key_type = Enum('type', ['reserved', 'optional', 'required'])
default_keys = {
    'application_name': key_type.reserved,
    'application_run_dir': key_type.reserved,
    'application_input_dir': key_type.reserved,
    'workload_name': key_type.reserved,
    'workload_run_dir': key_type.reserved,
    'workload_input_dir': key_type.reserved,
    'license_input_dir': key_type.reserved,
    'experiment_name': key_type.reserved,
    'experiment_run_dir': key_type.reserved,
    'experiment_status': key_type.reserved,
    'log_dir': key_type.reserved,
    'log_file': key_type.reserved,
    'err_file': key_type.reserved,
    'command': key_type.reserved,
    'env_path': key_type.reserved,
    'input_name': key_type.reserved,

    'spec_name': key_type.optional,
    'env_name': key_type.optional,

    'n_ranks': key_type.required,
    'n_nodes': key_type.required,
    'processes_per_node': key_type.required,
    'n_threads': key_type.required,
    'batch_submit': key_type.required,
    'mpi_command': key_type.required,
    'experiment_template_name': key_type.required,
}


class Keywords(object):
    """Class to represent known ramble keywords.

    Each keyword can have a type. Valid types are identified by the
    'key_type' variable as an enum.

    A map of keys, and their types is provided in the class level 'keys'
    variable. This enforces that each keyword can only have a single type.

    Current key types are:
      - Reserved: Ramble defines these, and a user should not be allowed to define them
      - Optional: Ramble can function with a definition from the user but it isn't required
      - Required: Ramble requires a definition for these. Ramble will try to set sensible defaults,
        but it might not be possible always.

    """
    def __init__(self, extra_keys={}):
        # Merge in additional Keys:
        self.keys = default_keys
        self.update_keys(extra_keys)

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
        return self.keys[key] == key_type.reserved

    def is_optional(self, key):
        """Check if a key is optional"""
        if not self.is_valid(key):
            return False
        return self.keys[key] == key_type.optional

    def is_required(self, key):
        """Check if a key is required"""
        if not self.is_valid(key):
            return False
        return self.keys[key] == key_type.required

    def check_reserved_keys(self, definitions):
        """Check a dictionary of variable definitions for reserved keywords"""
        if not definitions:
            return

        for definition in definitions.keys():
            if self.is_reserved(definition):
                raise RambleKeywordError(f'Keyword "{definition}" has been defined, ' +
                                         'but is reserved by ramble.')

    def check_required_keys(self, definitions):
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
            for key in required_set:
                ramble.util.logger.logger.warn(f'Required key "{key}" is not defined')
            raise RambleKeywordError('One or more required keys ' +
                                     'are not defined within an experiment.')


class RambleKeywordError(ramble.error.RambleError):
    """Superclass for all errors to do with Ramble Keywords"""


keywords = Keywords()
