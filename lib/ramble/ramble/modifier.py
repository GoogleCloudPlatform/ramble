# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for modifier definitions"""

import re
import six
import textwrap
import fnmatch
from typing import List

from llnl.util.tty.colify import colified

from ramble.language.modifier_language import ModifierMeta
from ramble.language.shared_language import SharedMeta, register_builtin  # noqa: F401
from ramble.error import RambleError
import ramble.util.colors as rucolor
import ramble.util.directives
from ramble.util.logger import logger


class ModifierBase(object, metaclass=ModifierMeta):
    name = None
    uses_spack = False
    _builtin_name = 'modifier_builtin::{obj_name}::{name}'
    _mod_prefix_builtin = r'modifier_builtin::'
    _language_classes = [ModifierMeta, SharedMeta]
    _pipelines = ['analyze', 'archive', 'mirror', 'setup', 'pushtocache', 'execute']

    modifier_class = 'ModifierBase'

    #: Lists of strings which contains GitHub usernames of attributes.
    #: Do not include @ here in order not to unnecessarily ping the users.
    maintainers: List[str] = []
    tags: List[str] = []

    def __init__(self, file_path):
        super().__init__()

        self._file_path = file_path
        self._on_executables = ['*']
        self.expander = None
        self._usage_mode = None

        self._verbosity = 'short'

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
        elif hasattr(self, '_default_usage_mode'):
            self._usage_mode = self._default_usage_mode
            logger.msg(f'    Using default usage mode {self._usage_mode} on modifier {self.name}')
        else:
            if len(self.modes) > 1 or len(self.modes) == 0:
                raise InvalidModeError('Cannot auto determine usage '
                                       f'mode for modifier {self.name}')

            self._usage_mode = list(self.modes.keys())[0]
            logger.msg(f'    Using default usage mode {self._usage_mode} on modifier {self.name}')

    def set_on_executables(self, on_executables):
        """Set the executables this modifier applies to.

        If given an empty list or a value of None, the default of: '*' is usage.
        """
        if on_executables:
            if not isinstance(on_executables, list):
                raise ModifierError(f'Modifier {self.name} given an unsupported on_executables '
                                    f'type of {type(on_executables)}')

            self._on_executables = []
            for exec_name in on_executables:
                self._on_executables.append(exec_name)
        else:
            self._on_executables = ['*']

    def inherit_from_application(self, app):
        self.expander = app.expander.copy()
        modded_vars = self.modded_variables(app)
        self.expander._variables.update(modded_vars)

    def _long_print(self):
        out_str = []
        out_str.append(rucolor.section_title('Modifier: ') + f'{self.name}\n')
        out_str.append('\n')

        out_str.append(rucolor.section_title('Description:\n'))
        if self.__doc__:
            out_str.append(f'\t{self.__doc__}\n')
        else:
            out_str.append('\tNone\n')

        if hasattr(self, 'tags'):
            out_str.append('\n')
            out_str.append(rucolor.section_title('Tags:\n'))
            out_str.append(colified(self.tags, tty=True))
            out_str.append('\n')

        if hasattr(self, 'modes'):
            out_str.append('\n')
            for mode_name, wl_conf in self.modes.items():
                out_str.append(rucolor.section_title('Mode:') + f' {mode_name}\n')

                if mode_name in self.modifier_variables:
                    out_str.append(rucolor.nested_1('\tVariables:\n'))
                    indent = '\t\t'
                    for var, conf in self.modifier_variables[mode_name].items():
                        out_str.append(rucolor.nested_2(f'{indent}{var}:\n'))
                        out_str.append(f'{indent}\tDescription: {conf["description"]}\n')
                        out_str.append(f'{indent}\tDefault: {conf["default"]}\n')
                        if 'values' in conf:
                            out_str.append(f'{indent}\tSuggested Values: {conf["values"]}\n')

                if mode_name in self.variable_modifications:
                    out_str.append(rucolor.nested_1('\tVariable Modifications:\n'))
                    indent = '\t\t'
                    for var, conf in self.variable_modifications[mode_name].items():
                        out_str.append(rucolor.nested_2(f'{indent}{var}:\n'))
                        out_str.append(f'{indent}\tMethod: {conf["method"]}\n')
                        out_str.append(f'{indent}\tModification: {conf["modification"]}\n')

            out_str.append('\n')

        if hasattr(self, 'builtins'):
            out_str.append(rucolor.section_title('Builtin Executables:\n'))
            out_str.append('\t' + colified(self.builtins.keys(), tty=True) + '\n')

        if hasattr(self, 'executable_modifiers'):
            out_str.append(rucolor.section_title('Executable Modifiers:\n'))
            out_str.append('\t' + colified(self.executable_modifiers.keys(), tty=True) + '\n')

        if hasattr(self, 'package_manager_configs'):
            out_str.append(rucolor.section_title('Package Manager Configs:\n'))
            for name, config in self.package_manager_configs.items():
                out_str.append(f'\t{name} = {config}\n')
            out_str.append('\n')

        if hasattr(self, 'compilers'):
            out_str.append(rucolor.section_title('Default Compilers:\n'))
            for comp_name, comp_def in self.compilers.items():
                out_str.append(rucolor.nested_2(f'\t{comp_name}:\n'))
                out_str.append(rucolor.nested_3('\t\tSpack Spec:') +
                               f'{comp_def["spack_spec"].replace("@", "@@")}\n')

                if 'compiler_spec' in comp_def and comp_def['compiler_spec']:
                    out_str.append(rucolor.nested_3('\t\tCompiler Spec:\n') +
                                   f'{comp_def["compiler_spec"].replace("@", "@@")}\n')

                if 'compiler' in comp_def and comp_def['compiler']:
                    out_str.append(rucolor.nested_3('\t\tCompiler:\n') +
                                   f'{comp_def["compiler"]}\n')
            out_str.append('\n')

        if hasattr(self, 'software_specs'):
            out_str.append(rucolor.section_title('Software Specs:\n'))
            for spec_name, spec_def in self.software_specs.items():
                out_str.append(rucolor.nested_2(f'\t{spec_name}:\n'))
                out_str.append(rucolor.nested_3('\t\tSpack Spec:') +
                               f'{spec_def["spack_spec"].replace("@", "@@")}\n')

                if 'compiler_spec' in spec_def and spec_def['compiler_spec']:
                    out_str.append(rucolor.nested_3('\t\tCompiler Spec:') +
                                   f'{spec_def["compiler_spec"].replace("@", "@@")}\n')

                if 'compiler' in spec_def and spec_def['compiler']:
                    out_str.append(rucolor.nested_3('\t\tCompiler:') +
                                   f'{spec_def["compiler"]}\n')
            out_str.append('\n')

        return out_str

    def _short_print(self):
        return [self.name]

    def __str__(self):
        if self._verbosity == 'long':
            return ''.join(self._long_print())
        elif self._verbosity == 'short':
            return ''.join(self._short_print())
        return self.name

    def format_doc(self, **kwargs):
        """Wrap doc string at 72 characters and format nicely"""
        indent = kwargs.get('indent', 0)

        if not self.__doc__:
            return ""

        doc = re.sub(r'\s+', ' ', self.__doc__)
        lines = textwrap.wrap(doc, 72)
        results = six.StringIO()
        for line in lines:
            results.write((" " * indent) + line + "\n")
        return results.getvalue()

    def modded_variables(self, app):
        mods = {}

        if self._usage_mode not in self.variable_modifications:
            return mods

        for var, var_mod in self.variable_modifications[self._usage_mode].items():
            if var_mod['method'] in ['append', 'prepend']:
                # var_str = app.expander.expansion_str(var)
                # prev_val = app.expander.expand_var(var_str)
                prev_val = app.variables[var]
                if var_mod['method'] == 'append':
                    mods[var] = f'{prev_val} {var_mod["modification"]}'
                else:  # method == prepend
                    mods[var] = f'{var_mod["modification"]} {prev_val}'
            else:  # method == set
                mods[var] = var_mod['modification']

        return mods

    def applies_to_executable(self, executable):
        apply = False

        mod_regex = re.compile(self._mod_prefix_builtin + f'{self.name}::')
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

        for action, conf in self.env_var_modifications[self._usage_mode].items():
            yield action, conf

    def all_package_manager_requirements(self):
        if self._usage_mode in self.package_manager_requirements:
            for req in self.package_manager_requirements[self._usage_mode]:
                yield req

    def all_pipeline_phases(self, pipeline):
        if pipeline in self.phase_definitions:
            for phase_name, phase_node in self.phase_definitions[pipeline].items():
                yield phase_name, phase_node

    def no_expand_vars(self):
        """Iterator over non-expandable variables in current mode

        Yields:
            (str): Variable name
        """

        if self._usage_mode in self.modifier_variables:
            for var, var_conf in self.modifier_variables[self._usage_mode].items():
                if not var_conf['expandable']:
                    yield var

    def mode_variables(self):
        """Return a dict of variables that should be defined for the current mode"""

        if self._usage_mode in self.modifier_variables:
            return self.modifier_variables[self._usage_mode]
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
            hook_func_name = f'_{hook_name}'
            if hasattr(self, hook_func_name):
                phase_func = getattr(self, hook_func_name)

                phase_func(workspace)

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
