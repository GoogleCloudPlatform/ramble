# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from enum import Enum

from ramble.namespace import namespace


# Can use auto() once we're at >= python 3.11
class ExperimentStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    UNQUEUED = "UNQUEUED"
    UNRESOLVED = "UNRESOLVED"  # unresolved means the status is not fetched successfully
    SETUP = "SETUP"
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


_OUTPUT_MAPPING = {
    "name": "name",
    namespace.n_repeats: "N_REPEATS",
    "keys": "keys",
    "contexts": "CONTEXTS",
    "software": "SOFTWARE",
    namespace.variables: "RAMBLE_VARIABLES",
    "raw_variables": "RAMBLE_RAW_VARIABLES",
    namespace.tags: "TAGS",
    namespace.variants: "VARIANTS",
    "experiment_chain": "EXPERIMENT_CHAIN",
    "success_criteria": "SUCCESS_CRITERIA",
}


# TODO: would be better to use dataclass after 3.6 support is dropped
class ExperimentResult:
    """Class containing results and related metadata of an experiment"""

    def __init__(self, app_inst):
        """Build up the result from the given app instance"""
        self.name = app_inst.expander.experiment_namespace

        self.status = app_inst.get_ramble_status()

        # Most libs can handle this str enum, but convert it to help out
        self.status = self.status.value

        self.n_repeats = app_inst.repeats.n_repeats
        self.experiment_chain = app_inst.chain_order.copy()
        self.tags = list(app_inst.experiment_tags)
        self.contexts = []
        self.success_criteria = {}
        self.software = {}

        self.keys = {}
        for key in app_inst.keywords.keys:
            if app_inst.keywords.is_key_level(key):
                self.keys[key] = app_inst.expander.expand_var_name(key)

        self.raw_variables = {}
        self.variables = {}
        for var, val in app_inst.variables.items():
            self.raw_variables[var] = val
            if var not in app_inst.keywords.keys or not app_inst.keywords.is_key_level(var):
                self.variables[var] = app_inst.expander.expand_var(val)

        self.variants = set()
        for _, obj_inst in app_inst._objects():
            if hasattr(obj_inst, "object_variants"):
                obj_var_set = obj_inst.object_variants.as_set()
                self.variants = self.variants.union(obj_var_set)
        self.variants = list(self.variants)

    def to_dict(self):
        """Generate a dict for encoders (json, yaml) and uploaders.

        The generated dict preserves the existing serialized format
        so that previous result files work as expected.
        """
        import copy

        output = {}
        obj_keys = {}

        obj_dict = copy.deepcopy(self.__dict__)

        if "keys" in obj_dict:
            obj_keys = obj_dict["keys"]

        for lookup_key, output_val in _OUTPUT_MAPPING.items():
            if lookup_key == "keys":
                output.update(obj_keys)
            else:
                output[output_val] = obj_dict[lookup_key]

        return output
