# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.namespace import namespace


_DICT_MAPPING = {
    "experiment_hash": "experiment_hash",
    "name": "name",
    "status": "RAMBLE_STATUS",
    "experiment_chain": "EXPERIMENT_CHAIN",
    namespace.n_repeats: "N_REPEATS",
    namespace.tags: "TAGS",
    namespace.variables: "RAMBLE_VARIABLES",
    "raw_variables": "RAMBLE_RAW_VARIABLES",
    "contexts": "CONTEXTS",
}


# TODO: would be better to use dataclass after 3.6 support is dropped
class ExperimentResult:
    """Class containing results and related metadata of an experiment"""

    def __init__(self, app_inst):
        """Build up the result from the given app instance"""
        self.name = app_inst.expander.experiment_namespace
        self.experiment_hash = app_inst.experiment_hash
        self.status = app_inst.get_status()
        self.n_repeats = app_inst.repeats.n_repeats
        self.experiment_chain = app_inst.chain_order.copy()
        self.tags = list(app_inst.experiment_tags)
        self.contexts = []

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

    def to_dict(self):
        """Generate a dict for encoders (json, yaml) and uploaders.

        The generated dict preserves the existing serialized format
        so that previous result files work as expected.
        """
        import copy

        obj_dict = copy.deepcopy(self.__dict__)
        if "keys" in obj_dict:
            res = obj_dict["keys"]
        else:
            res = {}
        for name, val in obj_dict.items():
            if name in _DICT_MAPPING:
                res[_DICT_MAPPING[name]] = val

        return res
