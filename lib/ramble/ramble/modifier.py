# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for modifier definitions"""

import io
import re
import textwrap
import fnmatch
from typing import List

from ramble.language.modifier_language import ModifierMeta, mode
from ramble.language.shared_language import SharedMeta
from ramble.error import RambleError
import ramble.util.directives
import ramble.util.class_attributes
from ramble.util.logger import logger
from ramble.util.naming import NS_SEPARATOR


class ModifierBase(metaclass=ModifierMeta):
    name = None
    _builtin_name = NS_SEPARATOR.join(("modifier_builtin", "{obj_name}", "{name}"))
    _mod_prefix_builtin = f"modifier_builtin{NS_SEPARATOR}"
    _language_classes = [ModifierMeta, SharedMeta]
    _pipelines = ["analyze", "archive", "mirror", "setup", "pushtocache", "execute"]

    modifier_class = "ModifierBase"

    #: Lists of strings which contains GitHub usernames of attributes.
    #: Do not include @ here in order not to unnecessarily ping the users.
    maintainers: List[str] = []
    tags: List[str] = []

    disabled = False

    mode("disabled", description="Mode to disable all modifier functionality")

    def __init__(self, file_path):
        super().__init__()

        ramble.util.class_attributes.convert_class_attributes(self)

        self._file_path = file_path
        self._on_executables = ["*"]
        self.expander = None
        self._usage_mode = None

        self._verbosity = "short"

        ramble.util.directives.define_directive_methods(self)

    def copy(self):
        """Deep copy a modifier instance"""
        new_copy = type(self)(self._file_path)
        new_copy._on_executables = self._on_executables.copy()
        new_copy._usage_mode = self._usage_mode
        new_copy._verbosity = self._verbosity

        return new_copy

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
            if len(non_disabled_modes) > 1 or len(non_disabled_modes) == 0:
                raise InvalidModeError(
                    "Cannot auto determine usage " f"mode for modifier {self.name}"
                )

            self._usage_mode = non_disabled_modes.pop()
            if len(logger.log_stack) >= 1:
                logger.msg(
                    f"    Using default usage mode {self._usage_mode} on modifier {self.name}"
                )

        if self._usage_mode == "disabled":
            self.disabled = True

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

            self._on_executables = []
            for exec_name in on_executables:
                self._on_executables.append(exec_name)
        else:
            self._on_executables = ["*"]

    def inherit_from_application(self, app):
        self.expander = app.expander.copy()
        modded_vars = self.modded_variables(app)
        self.expander._variables.update(modded_vars)

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

    def __str__(self):
        return self.name

    def format_doc(self, **kwargs):
        """Wrap doc string at 72 characters and format nicely"""
        indent = kwargs.get("indent", 0)

        if not self.__doc__:
            return ""

        doc = re.sub(r"\s+", " ", self.__doc__)
        lines = textwrap.wrap(doc, 72)
        results = io.StringIO()
        for line in lines:
            results.write((" " * indent) + line + "\n")
        return results.getvalue()

    def modded_variables(self, app, extra_vars={}):
        mods = {}

        if self._usage_mode not in self.variable_modifications:
            return mods

        for var, var_mod in self.variable_modifications[self._usage_mode].items():
            if var_mod["method"] in ["append", "prepend"]:
                if var in extra_vars:
                    prev_val = extra_vars[var]
                elif var in app.variables:
                    prev_val = app.variables[var]
                else:
                    prev_val = ""

                if prev_val != "" and prev_val is not None:
                    sep = var_mod["separator"]
                else:
                    sep = ""

                if var_mod["method"] == "append":
                    mods[var] = f'{prev_val}{sep}{var_mod["modification"]}'
                else:  # method == prepend
                    mods[var] = f'{var_mod["modification"]}{sep}{prev_val}'
            else:  # method == set
                mods[var] = var_mod["modification"]

        return mods

    def applies_to_executable(self, executable):
        apply = False

        mod_regex = re.compile(self._mod_prefix_builtin + f"{self.name}{NS_SEPARATOR}")
        for pattern in self._on_executables:
            if fnmatch.fnmatch(executable, pattern):
                apply = True

        exec_match = mod_regex.match(executable)
        if exec_match:
            apply = True

        return apply

    def apply_executable_modifiers(self, executable_name, executable, app_inst=None):
        pre_execs = []
        post_execs = []
        for exec_mod in self.executable_modifiers:
            mod_func = getattr(self, exec_mod)

            pre_exec, post_exec = mod_func(executable_name, executable, app_inst=app_inst)

            pre_execs.extend(pre_exec)
            post_execs.extend(post_exec)

        return pre_execs, post_execs

    def all_env_var_modifications(self):
        if self._usage_mode not in self.env_var_modifications:
            return

        yield from self.env_var_modifications[self._usage_mode].items()

    def all_package_manager_requirements(self):
        if self._usage_mode in self.package_manager_requirements:
            yield from self.package_manager_requirements[self._usage_mode]

    def all_pipeline_phases(self, pipeline):
        if pipeline in self.phase_definitions:
            yield from self.phase_definitions[pipeline].items()

    def no_expand_vars(self):
        """Iterator over non-expandable variables in current mode

        Yields:
            (str): Variable name
        """

        if self._usage_mode in self.modifier_variables:
            for var, var_conf in self.modifier_variables[self._usage_mode].items():
                if not var_conf.expandable:
                    yield var

    def mode_variables(self):
        """Return a dict of variables that should be defined for the current mode"""

        if self._usage_mode in self.modifier_variables:
            return self.modifier_variables[self._usage_mode]
        else:
            return {}

    def run_phase_hook(self, workspace, pipeline, hook_name):
        """Run a modifier hook.

        Hooks are internal functions named _{hook_name}.

        This is a wrapper to extract the hook function, and execute it
        properly.

        Hooks are only executed if they are not defined as a phase from the
        modifier.
        """

        run_hook = True
        if pipeline in self.phase_definitions:
            if hook_name in self.phase_definitions[pipeline]:
                run_hook = False

        if run_hook:
            hook_func_name = f"_{hook_name}"
            if hasattr(self, hook_func_name):
                phase_func = getattr(self, hook_func_name)

                phase_func(workspace)

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


class ModifierError(RambleError):
    """
    Exception that is raised by modifiers
    """


class InvalidModeError(ModifierError):
    """
    Exception raised when an invalid mode is passed
    """
