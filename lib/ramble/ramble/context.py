# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.namespace import namespace
import ramble.util.matrices

import spack.util.spack_yaml as syaml


class Context:
    """Class to represent a context

    This class contains variable definitions to store any individual context
    (such as application, workload, or experiment) and logic to merge in
    additional contexts by order of precedence."""

    def __init__(self):
        """Constructor for a Context

        Create a Context object, which holds context attributes.
        """
        self.env_variables = []
        self.variables = syaml.syaml_dict()
        self.variants = syaml.syaml_dict()
        self.internals = {}
        self.templates = None
        self.formatted_executables = {}
        self.chained_experiments = []
        self.modifiers = []
        self.context_name = None
        self.exclude = {}
        self.zips = {}
        self.matrices = []
        self.tags = []
        self.is_template = False
        self.n_repeats = 0

    def merge_context(self, in_context):
        """Merges another Context into this Context."""

        internal_sections = [
            namespace.custom_executables,
            namespace.executables,
            namespace.executable_injection,
        ]

        if in_context.variables:
            self.variables.update(in_context.variables)
        if in_context.variants:
            self.variants.update(in_context.variants)
        if in_context.env_variables:
            self.env_variables.append(in_context.env_variables)
        if in_context.internals:
            for internal_section in internal_sections:
                if internal_section in in_context.internals:
                    if isinstance(in_context.internals[internal_section], dict):
                        if internal_section not in self.internals:
                            self.internals[internal_section] = {}
                        section_dict = in_context.internals[internal_section]
                        for key, val in section_dict.items():
                            self.internals[internal_section][key] = val
                    elif isinstance(in_context.internals[internal_section], list):
                        if internal_section not in self.internals:
                            self.internals[internal_section] = []
                        self.internals[internal_section].extend(
                            in_context.internals[internal_section]
                        )
                    else:
                        self.internals[internal_section] = in_context.internals[internal_section]
        if in_context.chained_experiments:
            for chained_exp in in_context.chained_experiments:
                self.chained_experiments.append(chained_exp.copy())
        if in_context.modifiers:
            for modifier in in_context.modifiers:
                self.modifiers.append(modifier.copy())
        if in_context.templates is not None:
            self.is_template = in_context.templates
        if in_context.exclude:
            self.exclude = in_context.exclude
        if in_context.zips:
            self.zips.update(in_context.zips)
        if in_context.matrices:
            self.matrices = in_context.matrices
        if in_context.tags:
            self.tags.extend(in_context.tags)
        if in_context.n_repeats != 0:
            self.n_repeats = int(in_context.n_repeats)
        if in_context.formatted_executables:
            self.formatted_executables.update(in_context.formatted_executables)


def create_context_from_dict(context_name, in_dict):
    """Creates a new Context object from an input dictionary

    Dictionaries should follow the below format:

    in_dict = {
        'env_vars': [],
        'variables': {},
        'variants': {},
        'internals': {},
        'template': '',
        'chained_experiments': [],
        'modifiers': [],
        'context_name': '',
        'exclude': {},
        'zips': {},
        'matrices': {} or [],
        'tags': []
        'n_repeats': '',

    Args:
        context_name: The name of the context (e.g., application name)
        in_dict: A dictionary representing the variable definitions

    Returns:
        Context(object)
    """

    new_context = Context()

    new_context.context_name = context_name

    if namespace.env_var in in_dict:
        new_context.env_variables = in_dict[namespace.env_var]

    if namespace.variables in in_dict:
        new_context.variables = in_dict[namespace.variables]

    if namespace.variants in in_dict:
        new_context.variants = in_dict[namespace.variants]

    if namespace.internals in in_dict:
        new_context.internals = in_dict[namespace.internals]

    if namespace.template in in_dict:
        new_context.templates = in_dict[namespace.template]

    if namespace.chained_experiments in in_dict:
        new_context.chained_experiments = in_dict[namespace.chained_experiments]

    if namespace.modifiers in in_dict:
        new_context.modifiers = in_dict[namespace.modifiers]

    if namespace.exclude in in_dict:
        new_context.exclude = in_dict[namespace.exclude]

    if namespace.zips in in_dict:
        new_context.zips = in_dict[namespace.zips]

    if namespace.tags in in_dict:
        new_context.tags = in_dict[namespace.tags].copy()

    new_context.matrices = ramble.util.matrices.extract_matrices(
        "experiment creation", context_name, in_dict
    )

    if namespace.n_repeats in in_dict:
        new_context.n_repeats = int(in_dict[namespace.n_repeats])

    if namespace.formatted_executables in in_dict:
        new_context.formatted_executables = in_dict[namespace.formatted_executables].copy()

    return new_context
