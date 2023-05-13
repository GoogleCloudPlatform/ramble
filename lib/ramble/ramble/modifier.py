# Copyright 2022-2023 Google LLC
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

from llnl.util.tty.colify import colified

from ramble.language.modifier_language import ModifierMeta, register_builtin  # noqa: F401
from ramble.error import RambleError


header_color = '@*b'
level1_color = '@*g'
level2_color = '@*r'
plain_format = '@.'


def section_title(s):
    return header_color + s + plain_format


def subsection_title(s):
    return level1_color + s + plain_format


def nested_2_color(s):
    return level2_color + s + plain_format


class ModifierBase(object, metaclass=ModifierMeta):
    name = None
    uses_spack = False
    _exec_prefix_builtin = 'builtin::'
    _builtin_required_key = 'required'

    modifier_class = 'ModifierBase'

    def __init__(self, file_path):
        super().__init__()

        self._file_path = file_path

        self._verbosity = 'short'

    def copy(self):
        """Deep copy a modifier instance"""
        new_copy = type(self)(self._file_path)

        return new_copy

    def _long_print(self):
        out_str = []
        out_str.append(section_title('Modifier: ') + f'{self.name}\n')
        out_str.append('\n')

        out_str.append('%s\n' % section_title('Description:'))
        if self.__doc__:
            out_str.append('\t%s\n' % self.__doc__)
        else:
            out_str.append('\tNone\n')

        if hasattr(self, 'tags'):
            out_str.append('\n')
            out_str.append('%s\n' % section_title('Tags:'))
            out_str.append(colified(self.tags, tty=True))
            out_str.append('\n')

        if hasattr(self, 'modes'):
            out_str.append('\n')
            for mode_name, wl_conf in self.modes.items():
                out_str.append(section_title('Mode:') + f' {mode_name}\n')

                if mode_name in self.variable_modifications:
                    out_str.append('\t' + subsection_title('Variable Modifications:') + '\n')
                    for var, conf in self.variable_modifications[mode_name].items():
                        indent = '\t\t'

                        out_str.append(nested_2_color(f'{indent}{var}:\n'))
                        out_str.append(f'{indent}\tMethod: {conf["method"]}\n')
                        out_str.append(f'{indent}\tModification: {conf["modification"]}\n')

            out_str.append('\n')

        if hasattr(self, 'builtins'):
            out_str.append(section_title('Builtin Executables:\n'))
            out_str.append('\t' + colified(self.builtins.keys(), tty=True) + '\n')
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

    def apply_executable_modifiers(self, executable_name, executable):
        pre_execs = []
        post_execs = []
        for exec_mod in self.executable_modifiers:
            mod_func = getattr(self, exec_mod)

            pre_exec, post_exec = mod_func(executable_name, executable)

            pre_execs.extend(pre_exec)
            post_execs.extend(post_exec)

        return pre_execs, post_execs

    def all_env_var_modifications(self):
        if self._usage_mode not in self.env_var_modifications:
            return

        for action, conf in self.env_var_modifications[self._usage_mode].items():
            yield action, conf


class ModifierError(RambleError):
    """
    Exception that is raised by modifiers
    """


class InvalidModeError(ModifierError):
    """
    Exception raised when an invalid mode is passed
    """
