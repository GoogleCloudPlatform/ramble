# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for modifier definitions"""

import fnmatch
import re
from typing import List

import ramble.repository
import ramble.util.class_attributes
import ramble.util.directives
import ramble.variants
from ramble.error import InvalidModeError, ModifierError
from ramble.language.modifier_language import ModifierMeta, mode
from ramble.language.shared_language import SharedMeta
from ramble.util.logger import logger
from ramble.util.naming import NS_SEPARATOR

ObjectMixin = ramble.repository.get_base_class("object_mixin")


class ModifierBase(ObjectMixin, metaclass=ModifierMeta):
    name = None
    origin_type = "modifier"
    _builtin_name = NS_SEPARATOR.join(
        ("modifier_builtin", "{obj_name}", "{name}")
    )
    _mod_prefix_builtin = f"modifier_builtin{NS_SEPARATOR}"
    _language_classes = [ModifierMeta, SharedMeta]
    _pipelines = [
        "analyze",
        "archive",
        "mirror",
        "setup",
        "pushtocache",
        "execute",
        "logs",
    ]

    modifier_class = "ModifierBase"

    #: Lists of strings which contains GitHub usernames of attributes.
    #: Do not include @ here in order not to unnecessarily ping the users.
    maintainers: List[str] = []
    tags: List[str] = []

    disabled = False

    mode("disabled", description="Mode to disable all modifier functionality")

    def __init__(self, file_path):
        super().__init__()

        self.object_variants = ramble.variants.VariantSet()
        for var_args in self.class_variants.values():
            self.object_variants.default_variant(**var_args)

        ramble.util.class_attributes.convert_class_attributes(self)

        self._file_path = file_path
        self._on_executables = ["*"]
        self.expander = None
        self._usage_mode = None
        self.app_inst = None

        self._verbosity = "short"

        self._mod_regex = re.compile(
            self._mod_prefix_builtin + f"{self.name}{NS_SEPARATOR}"
        )

        ramble.util.directives.define_directive_methods(self)

    def copy(self):
        """Deep copy a modifier instance"""
        new_copy = super().copy()
        new_copy._on_executables = self._on_executables.copy()
        new_copy._usage_mode = self._usage_mode

        return new_copy

    def satisfy_when(self, when_key):
        return self.expander.satisfies(when_key, self.object_variants)

    def set_usage_mode(self, mode):
        """Set the usage mode for this modifier.

        If not set, or given an empty string the modifier tries to auto-detect a mode.

        If it cannot auto detect the usage mode, an error is raised.
        """
        if mode:
            self._usage_mode = mode
        elif hasattr(self, "_default_usage_mode"):
            self._usage_mode = self._default_usage_mode
            if len(logger.log_stack) >= 1:
                logger.msg(
                    f"    Using default usage mode {self._usage_mode} on modifier {self.name}"
                )
        else:
            non_disabled_modes = set(self.modes)
            non_disabled_modes.remove("disabled")
            if len(non_disabled_modes) != 1:
                raise InvalidModeError(
                    "Cannot auto determine usage "
                    f"mode for modifier {self.name}"
                )

            self._usage_mode = non_disabled_modes.pop()
            if len(logger.log_stack) >= 1:
                logger.msg(
                    f"    Using default usage mode {self._usage_mode} on modifier {self.name}"
                )

        if self._usage_mode == "disabled":
            self.disabled = True

    def set_modifier_variants(self):
        """Set the variants for this modifier.

        Requires usage mode to be set first."""
        self.object_variants.multi_value_variant(
            "modifier",
            value=self.name,
        )

        self.object_variants.multi_value_variant(
            f"{self.name}_mode",
            value=self._usage_mode,
        )

    def set_on_executables(self, on_executables):
        """Set the executables this modifier applies to.

        If given an empty list or a value of None, the default of: '*' is usage.
        """
        if on_executables:
            if not isinstance(on_executables, list):
                raise ModifierError(
                    f"Modifier {self.name} given an unsupported on_executables "
                    f"type of {type(on_executables)}"
                )

            self._on_executables = list(on_executables)
        else:
            self._on_executables = ["*"]

    def inherit_from_application(self, app):
        self.expander = app.expander.copy()
        self.object_variants.merge_default_variants(app.object_variants)

        for name, value in app.variants.items():
            expanded_value = self.expander.expand_var(value, typed=True)
            self.object_variants.experiment_variant(name, expanded_value)

        self.object_variants.merge_multi_value_variants(app.object_variants)
        modded_vars = self.modded_variables(app)
        self.expander._variables.update(modded_vars)
        self.app_inst = app

    def define_variable(self, var_name, var_value):
        """Define a variable within this modifier's expander instance"""
        self.expander._variables[var_name] = var_value

    def modify_experiment(self, app):
        """Stubbed method to allow modification of experiment variables before
        an experiment is completely defined.

        This can be used to define things like n_ranks and have it influence
        the name of the resulting experiment.
        """
        pass

    def modded_variables(self, app, extra_vars=None):
        mods = {}

        if extra_vars is None:
            extra_vars = {}

        for when_set, var_mod_dict in self.variable_modifications.items():
            if self.expander.satisfies(when_set, self.object_variants):
                for var, var_mods in var_mod_dict.items():
                    for var_mod in var_mods:
                        if var_mod.method in ["append", "prepend"]:
                            if var in mods:
                                prev_val = mods[var]
                            elif var in extra_vars:
                                prev_val = extra_vars[var]
                            elif var in app.variables:
                                prev_val = app.variables[var]
                            else:
                                prev_val = ""

                            if prev_val:
                                sep = var_mod.separator
                            else:
                                sep = ""

                            if var_mod.method == "append":
                                mods[var] = (
                                    f"{prev_val}{sep}{var_mod.modification}"
                                )
                            else:  # method == prepend
                                mods[var] = (
                                    f"{var_mod.modification}{sep}{prev_val}"
                                )
                        else:  # method == set
                            mods[var] = var_mod.modification

        return mods

    def applies_to_executable(self, executable):
        """Check if this modifier applies to a given executable name."""
        if any(
            fnmatch.fnmatch(executable, pattern)
            for pattern in self._on_executables
        ):
            return True

        return bool(self._mod_regex.match(executable))

    def apply_executable_modifiers(
        self, executable_name, executable, app_inst=None
    ):
        pre_execs = []
        post_execs = []
        for when_set, exec_mods in self.executable_modifiers.items():
            if self.expander.satisfies(when_set, self.object_variants):
                for exec_mod in exec_mods:
                    mod_func = getattr(self, exec_mod)

                    pre_exec, post_exec = mod_func(
                        executable_name, executable, app_inst=app_inst
                    )

                    pre_execs.extend(pre_exec)
                    post_execs.extend(post_exec)

        return pre_execs, post_execs

    def all_env_var_modifications(self):
        for when_set, env_var_mods in self.env_var_modifications.items():
            if not self.expander.satisfies(when_set, self.object_variants):
                continue

            yield from env_var_mods.values()

    def all_package_manager_requirements(self):
        for when_set in self.package_manager_requirements:
            if not self.expander.satisfies(when_set, self.object_variants):
                continue

            yield from self.package_manager_requirements[when_set]

    def no_expand_vars(self):
        """Iterator over non-expandable variables in current mode

        Yields:
            (str): Variable name
        """

        for when_key, var_list in self.object_variables.items():
            if not self.expander.satisfies(when_key, self.object_variants):
                continue

            for var in var_list:
                if not var.expandable:
                    yield var.name

    def artifact_inventory(self, workspace, app_inst=None):
        """Return an inventory of modifier artifacts

        Artifact inventories are up to the individual modifier to define the
        format of.

        This will then show up in an experiment inventory.

        Returns:
            (Any) Artifact inventory for this modifier
        """

        return None

    def _prepare_analysis(self, workspace):
        """Hook to perform analysis that a modifier defines.

        This function allows modifier definitions to inject their own
        processing to output files, before FOMs are extracted.
        """
        pass
