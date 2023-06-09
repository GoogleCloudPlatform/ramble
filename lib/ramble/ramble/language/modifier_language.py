# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.language.language_base
from ramble.language.language_base import DirectiveError


class ModifierMeta(ramble.language.language_base.DirectiveMeta):
    _directive_names = set()
    _diretives_to_be_executed = []


modifier_directive = ModifierMeta.directive


@modifier_directive('figure_of_merit_contexts')
def figure_of_merit_context(name, regex, output_format):
    """Defines a context for figures of merit

    Defines a new context to contain figures of merit.

    Inputs:
     - name: High level name of the context. Can be referred to in
             the figure of merit
     - regex: Regular expression, using group names, to match a context.
     - output_format: String, using python keywords {group_name} to
                      extract group names from context regular
                      expression.
    """

    def _execute_figure_of_merit_context(mod):
        mod.figure_of_merit_contexts[name] = {
            'regex': regex,
            'output_format': output_format
        }

    return _execute_figure_of_merit_context


@modifier_directive('archive_patterns')
def archive_pattern(pattern):
    """Adds a file pattern to be archived in addition to figure of merit logs

    Defines a new file pattern that will be archived during workspace archival.
    Archival will only happen for files that match the pattern when archival
    is being performed.

    Inputs:
      - pattern: Pattern that refers to files to archive
    """

    def _execute_archive_pattern(mod):
        mod.archive_patterns[pattern] = pattern

    return _execute_archive_pattern


@modifier_directive('figures_of_merit')
def figure_of_merit(name, fom_regex, group_name, units='', log_file='{log_file}',
                    contexts=[]):
    """Adds a figure of merit to track for this modifier

    Defines a new figure of merit.
    Inputs:
     - name: High level name of the figure of merit
     - log_file: File the figure of merit can be extracted from
     - fom_regex: A regular expression using named groups to extract the FOM
     - group_name: The name of the group that the FOM should be pulled from
     - units: The units associated with the FOM
     - keep_policy: The policy for determining which FOM(s) to keep
                    can be 'last' or 'all'
    """

    def _execute_figure_of_merit(mod):
        mod.figures_of_merit[name] = {
            'log_file': log_file,
            'regex': fom_regex,
            'group_name': group_name,
            'units': units,
            'contexts': contexts
        }

    return _execute_figure_of_merit


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
    - name: The variable to modify
    - modification: The value to modify 'name' with
    - method: How the modification should be applied. Supported values are
              'append', 'prepend', and 'set'
       - 'append' will add the modification to the end of 'name'
       - 'prepend' will add the modification to the beginning of 'name'
       - 'set' (Default) will overwrite 'name' with the modification
    - mode: Single mode to group this modification into
    - modes: List of modes to group this modification into
    """

    def _execute_variable_modification(mod):
        supported_methods = ['append', 'prepend', 'set']
        if not (mode or modes):
            raise DirectiveError('variable_modification directive requires:\n' +
                                 '  mode or modes to be defined.')

        if method not in supported_methods:
            raise DirectiveError('variable_modification directive given an invalid method.\n'
                                 f'  Valid methods are {str(supported_methods)}')

        all_modes = []
        if mode:
            all_modes.append(mode)
        if modes:
            if isinstance(modes, list):
                all_modes.extend(modes)
            else:
                all_modes.extend(modes)

        for mode_name in all_modes:
            if mode_name not in mod.variable_modifications:
                mod.variable_modifications[mode_name] = {}

            mod.variable_modifications[mode_name][name] = {
                'modification': modification,
                'method': method,
            }

    return _execute_variable_modification


@modifier_directive('software_specs')
def software_spec(name, spack_spec, compiler_spec=None, compiler=None):
    """Defines a new software spec needed for this modifier.

    Adds a new software spec (for spack to use) that this modifier
    needs to execute properly.

    Only adds specs to modifiers that use spack.

    Specs can be described as an mpi spec, which means they
    will depend on the MPI library within the resulting spack
    environment.
    """

    def _execute_software_spec(mod):
        if mod.uses_spack:

            # Define the spec
            mod.software_specs[name] = {
                'spack_spec': spack_spec,
                'compiler_spec': compiler_spec,
                'compiler': compiler
            }

    return _execute_software_spec


@modifier_directive('default_compilers')
def default_compiler(name, spack_spec, compiler_spec=None, compiler=None):
    """Defines the default compiler that will be used with this modifier

    Adds a new compiler spec to this modifier. Software specs should
    reference a compiler that has been added.
    """

    def _execute_default_compiler(mod):
        if mod.uses_spack:
            mod.default_compilers[name] = {
                'spack_spec': spack_spec,
                'compiler_spec': compiler_spec,
                'compiler': compiler
            }

    return _execute_default_compiler


@modifier_directive('required_packages')
def required_package(name):
    """Defines a new spack package that is required for this modifier
    to function properly.
    """

    def _execute_required_package(mod):
        if mod.uses_spack:
            mod.required_packages[name] = True

    return _execute_required_package


@modifier_directive('builtins')
def register_builtin(name, required=True, injection_method='prepend'):
    """Register a builtin

    Builtins are methods that return lists of strings. These methods represent
    a way to write python code to generate executables for building up
    workloads.

    Builtins can be referred to in a list of executables as:
    `modifier_builtin::modifier_name::method_name`.
    As an example, if a modifier named 'test-modifier' had a builtin defined as follows:

    ```
    register_builtin('mod_builtin', required=True)
    def mod_builtin(self):
       ...
    ```

    Its fully qualified name would be 'modifier_builtin::test-modifier::mod_builtin'

    The 'required' attribute marks a builtin as required for all workloads. This
    will ensure the builtin is added to the workload if it is not explicitly
    added. If required builtins are not explicitly added to a workload, they
    are injected at the beginning of the list of executables.

    Modifier classes that want to disable auto-injecting a builtin into
    the experiment executable lists can use:
    ```
    register_builtin('mod_builtin', required=False)
    ```
    In order to use a non-required builtin, the experiment will need to
    explicitly list the builtin in their executable list.

    The 'injection_method' attribute controls where the builtin will be
    injected into the executable list.
    Options are:
    - 'prepend' -- This builtin will be injected at the beginning of the executable list
    - 'append' -- This builtin will be injected at the end of the executable list
    """
    supported_injection_methods = ['prepend', 'append']

    def _store_builtin(mod):
        if injection_method not in supported_injection_methods:
            raise DirectiveError(f'Modifier {mod.name} has an invalid '
                                 f'injection method of {injection_method}.\n'
                                 f'Valid methods are {str(supported_injection_methods)}')
        builtin_name = f'modifier_builtin::{mod.name}::{name}'
        mod.builtins[builtin_name] = {'name': name,
                                      'required': required,
                                      'injection_method': injection_method}
    return _store_builtin


@modifier_directive('executable_modifiers')
def executable_modifier(name):
    """Register an executable modifier

    Executable modifiers can modify various aspects of non-builtin application
    executable definitions.

    These behave similarly to builtins, in that a python method defines the
    actual modifications

    For example:

    ```
    executable_modifier('write_exec_name')

    def write_exec_name(self, executable_name, executable):
      prepend_execs = []
      append_execs = [ExecutableCommand(
          template='echo "{executable_name}"',
          mpi=False,
          redirect='{log_file}',
          output_capture=OUTPUT_CAPTURE.DEFAULT
      )]

      return prepend_execs, append_execs
    ```

    Would append the `echo "{executable_name}"` to every non-builtin executable
    in an experiment.

    Executable modifiers are allowed to modify the input executable in place.
    Executable modifiers must return two lists of executables.
    Returns:
    - prepend_execs: List of executables to inject before the base executable
    - append_execs: List of executables to inject after the base executable
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
    - name: The name of the environment variable that will be modified
    - modification: The value of the modification
    - method: The method of the modification.
    - mode: Name of mode this env_var_modification should apply in
    - modes: List of mode names this env_var_modification should apply in

    Supported values for method are:
    - set: Defines the variable to equal the modification value
    - unset: Removes any definition of the variable from the environment
    - prepend: Prepends the modification to the beginning of the variable.
               Always uses the separator ':'
    - append: Appends the modification value to the end of the value. Allows a
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

        if not (mode or modes):
            raise DirectiveError('env_var_modification directive requires:\n' +
                                 '  mode or modes to be defined.')

        all_modes = []
        if mode:
            all_modes.append(mode)
        if modes:
            if isinstance(modes, list):
                all_modes.extend(modes)
            else:
                all_modes.append(modes)

        for set_mode in all_modes:
            if set_mode not in mod.env_var_modifications:
                mod.env_var_modifications[mode] = {}

        # Set requires a dict, everything else requires a list.
        if method == 'set':
            for set_mode in all_modes:
                if method not in mod.env_var_modifications[mode]:
                    mod.env_var_modifications[mode][method] = {}
                mod.env_var_modifications[mode][method][name] = modification
            return

        for set_mode in all_modes:
            if method not in mod.env_var_modifications[mode]:
                mod.env_var_modifications[mode][method] = []

        # If unset, exit early
        if method == 'unset':
            for set_mode in all_modes:
                mod.env_var_modifications[mode][method].append(name)
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

        for set_mode in all_modes:
            mod.env_var_modifications[mode][method].append(append_dict.copy())

    return _env_var_modification


@modifier_directive(dicts=())
def maintainers(*names: str):
    """Add a new maintainer directive, to specify maintainers in a declarative way.

    Args:
        names: GitHub username for the maintainer
    """

    def _execute_maintainer(mod):
        maintainers_from_base = getattr(mod, "maintainers", [])
        # Here it is essential to copy, otherwise we might add to an empty list in the parent
        mod.maintainers = list(sorted(set(maintainers_from_base + list(names))))

    return _execute_maintainer


@modifier_directive(dicts=())
def tags(*values: str):
    """Add a new tag directive, to specify tags in a declarative way.

    Args:
        values: Value to mark as a tag
    """

    def _execute_tag(mod):
        tags_from_base = getattr(mod, "tags", [])
        # Here it is essential to copy, otherwise we might add to an empty list in the parent
        mod.tags = list(sorted(set(tags_from_base + list(values))))

    return _execute_tag
