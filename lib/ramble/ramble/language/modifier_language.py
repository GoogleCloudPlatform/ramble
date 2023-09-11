# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.language.language_helpers
import ramble.language.language_base
import ramble.language.shared_language
from ramble.language.language_base import DirectiveError


class ModifierMeta(ramble.language.shared_language.SharedMeta):
    _directive_names = set()
    _directives_to_be_executed = []


modifier_directive = ModifierMeta.directive


@modifier_directive('modes')
def mode(name, description, **kwargs):
    """Define a new mode for this modifier.

    Modes allow a modifier to bundle a set of modifications together.
    """

    def _execute_mode(mod):
        mod.modes[name] = {
            'description': description
        }

    return _execute_mode


@modifier_directive('variable_modifications')
def variable_modification(name, modification, method='set', mode=None, modes=None, **kwargs):
    """Define a new variable modification for a mode in this modifier.

    A variable modification will apply a change to a defined variable within an experiment.

    Args:
        name: The variable to modify
        modification: The value to modify 'name' with
        method: How the modification should be applied
        mode: Single mode to group this modification into
        modes: List of modes to group this modification into

    Supported values are 'append', 'prepend', and 'set':

      'append' will add the modification to the end of 'name'

      'prepend' will add the modification to the beginning of 'name'

      'set' (Default) will overwrite 'name' with the modification

    """

    def _execute_variable_modification(mod):
        supported_methods = ['append', 'prepend', 'set']
        if method not in supported_methods:
            raise DirectiveError('variable_modification directive given an invalid method.\n'
                                 f'  Valid methods are {str(supported_methods)}')

        all_modes = ramble.language.language_helpers.require_definition(mode,
                                                                        modes,
                                                                        'mode',
                                                                        'modes',
                                                                        'variable_modification')

        for mode_name in all_modes:
            if mode_name not in mod.variable_modifications:
                mod.variable_modifications[mode_name] = {}

            mod.variable_modifications[mode_name][name] = {
                'modification': modification,
                'method': method,
            }

    return _execute_variable_modification


@modifier_directive('executable_modifiers')
def executable_modifier(name):
    """Register an executable modifier

    Executable modifiers can modify various aspects of non-builtin application
    executable definitions.

    These behave similarly to builtins, in that a python method defines the
    actual modifications

    For example:

    .. code-block:: python

      executable_modifier('write_exec_name')

      def write_exec_name(self, executable_name, executable, app_inst=None):
        prepend_execs = []
        append_execs = [ExecutableCommand(
            template='echo "{executable_name}"',
            mpi=False,
            redirect='{log_file}',
            output_capture=OUTPUT_CAPTURE.DEFAULT
        )]

        return prepend_execs, append_execs

    Would append the `echo "{executable_name}"` to every non-builtin executable
    in an experiment.

    Executable modifiers are allowed to modify the input executable in place.
    Executable modifiers must return two lists of executables.

    Returns:
      prepend_execs: List of executables to inject before the base executable
      append_execs: List of executables to inject after the base executable
    """
    def _executable_modifier(mod):
        mod.executable_modifiers[name] = name

    return _executable_modifier


@modifier_directive('env_var_modifications')
def env_var_modification(name, modification=None, method='set', mode=None, modes=None, **kwargs):
    """Define an environment variable modifier

    Environment variable modifications modify the values of environment
    variables within the application instance.

    Args:
        name: The name of the environment variable that will be modified
        modification: The value of the modification
        method: The method of the modification.
        mode: Name of mode this env_var_modification should apply in
        modes: List of mode names this env_var_modification should apply in

    Supported values for method are:
    set: Defines the variable to equal the modification value

    unset: Removes any definition of the variable from the environment

    prepend: Prepends the modification to the beginning of the variable.
    Always uses the separator ':'

    append: Appends the modification value to the end of the value. Allows a
    keyword argument of 'separator' to define the delimiter between values.

    """
    def _env_var_modification(mod):
        supported_methods = ['set', 'unset', 'append', 'prepend']
        if method not in supported_methods:
            raise DirectiveError('env_var_modification directive given an invalid method of '
                                 f'{method}. Supported methods are {str(supported_methods)}')

        if method != 'unset' and not modification:
            raise DirectiveError(f'env_var_modification directive with method {method} '
                                 'requires a value for the modification argument.')

        all_modes = ramble.language.language_helpers.require_definition(mode,
                                                                        modes,
                                                                        'mode',
                                                                        'modes',
                                                                        'env_var_modification')

        for mode_name in all_modes:
            if mode_name not in mod.env_var_modifications:
                mod.env_var_modifications[mode_name] = {}

        # Set requires a dict, everything else requires a list.
        if method == 'set':
            for mode_name in all_modes:
                if method not in mod.env_var_modifications[mode_name]:
                    mod.env_var_modifications[mode_name][method] = {}
                mod.env_var_modifications[mode_name][method][name] = modification
            return

        for mode_name in all_modes:
            if method not in mod.env_var_modifications[mode_name]:
                mod.env_var_modifications[mode_name][method] = []

        # If unset, exit early
        if method == 'unset':
            for mode_name in all_modes:
                mod.env_var_modifications[mode_name][method].append(name)
            return

        append_dict = {}
        separator = ':'
        if method == 'append' and 'separator' in kwargs:
            separator = kwargs['separator']

        append_name = 'paths'
        if separator != ':':
            append_name = 'vars'
            append_dict['var-separator'] = separator

        append_dict[append_name] = {}
        append_dict[append_name][name] = modification

        for mode_name in all_modes:
            mod.env_var_modifications[mode_name][method].append(append_dict.copy())

    return _env_var_modification
