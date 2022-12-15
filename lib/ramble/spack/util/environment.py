# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
"""Utilities for setting and modifying environment variables."""
import collections
import contextlib
import inspect
import json
import os
import os.path
import platform
import re
import socket
import sys

import six
from six.moves import cPickle
from six.moves import shlex_quote as cmd_quote

import llnl.util.tty as tty
from llnl.util.lang import dedupe

import spack.config
import spack.platforms
import spack.spec
import spack.util.executable as executable
import spack.util.spack_json as sjson
from spack.util.path import path_to_os_path, system_path_filter

is_windows = sys.platform == 'win32'

system_paths = ['/', '/usr', '/usr/local'] if \
    not is_windows else ['C:\\', 'C:\\Program Files',
                         'C:\\Program Files (x86)', 'C:\\Users',
                         'C:\\ProgramData']
suffixes = ['bin', 'bin64', 'include', 'lib', 'lib64'] if not is_windows else []
system_dirs = [os.path.join(p, s) for s in suffixes for p in system_paths] + \
    system_paths


_shell_set_strings = {
    'sh': 'export {0}={1};\n',
    'csh': 'setenv {0} {1};\n',
    'fish': 'set -gx {0} {1};\n',
    'bat': 'set "{0}={1}"\n'
}


_shell_unset_strings = {
    'sh': 'unset {0};\n',
    'csh': 'unsetenv {0};\n',
    'fish': 'set -e {0};\n',
    'bat': 'set "{0}="\n'
}


tracing_enabled = False


def is_system_path(path):
    """Predicate that given a path returns True if it is a system path,
    False otherwise.

    Args:
        path (str): path to a directory

    Returns:
        True or False
    """
    return path and os.path.normpath(path) in system_dirs


def filter_system_paths(paths):
    """Return only paths that are not system paths."""
    return [p for p in paths if not is_system_path(p)]


def deprioritize_system_paths(paths):
    """Put system paths at the end of paths, otherwise preserving order."""
    filtered_paths = filter_system_paths(paths)
    fp = set(filtered_paths)
    return filtered_paths + [p for p in paths if p not in fp]


def prune_duplicate_paths(paths):
    """Returns the paths with duplicates removed, order preserved."""
    return list(dedupe(paths))


def get_path(name):
    path = os.environ.get(name, "").strip()
    if path:
        return path.split(os.pathsep)
    else:
        return []


def env_flag(name):
    if name in os.environ:
        value = os.environ[name].lower()
        return value == "true" or value == "1"
    return False


def path_set(var_name, directories):
    path_str = os.pathsep.join(str(dir) for dir in directories)
    os.environ[var_name] = path_str


def path_put_first(var_name, directories):
    """Puts the provided directories first in the path, adding them
       if they're not already there.
    """
    path = os.environ.get(var_name, "").split(os.pathsep)

    for dir in directories:
        if dir in path:
            path.remove(dir)

    new_path = tuple(directories) + tuple(path)
    path_set(var_name, new_path)


bash_function_finder = re.compile(r'BASH_FUNC_(.*?)\(\)')


def env_var_to_source_line(var, val):
    if var.startswith('BASH_FUNC'):
        source_line = 'function {fname}{decl}; export -f {fname}'.\
                      format(fname=bash_function_finder.sub(r'\1', var),
                             decl=val)
    else:
        source_line = '{var}={val}; export {var}'.format(var=var,
                                                         val=cmd_quote(val))
    return source_line


@system_path_filter(arg_slice=slice(1))
def dump_environment(path, environment=None):
    """Dump an environment dictionary to a source-able file."""
    use_env = environment or os.environ
    hidden_vars = set(['PS1', 'PWD', 'OLDPWD', 'TERM_SESSION_ID'])

    fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
    with os.fdopen(fd, 'w') as env_file:
        for var, val in sorted(use_env.items()):
            env_file.write(''.join(['#' if var in hidden_vars else '',
                                    env_var_to_source_line(var, val),
                                    '\n']))


@system_path_filter(arg_slice=slice(1))
def pickle_environment(path, environment=None):
    """Pickle an environment dictionary to a file."""
    cPickle.dump(dict(environment if environment else os.environ),
                 open(path, 'wb'), protocol=2)


def get_host_environment_metadata():
    """Get the host environment, reduce to a subset that we can store in
    the install directory, and add the spack version.
    """
    import spack.main
    environ = get_host_environment()
    return {"host_os": environ['os'],
            "platform": environ['platform'],
            "host_target": environ['target'],
            "hostname": environ['hostname'],
            "spack_version": spack.main.get_version(),
            "kernel_version": platform.version()}


def get_host_environment():
    """Return a dictionary (lookup) with host information (not including the
    os.environ).
    """
    host_platform = spack.platforms.host()
    host_target = host_platform.target('default_target')
    host_os = host_platform.operating_system('default_os')
    arch_fmt = 'platform={0} os={1} target={2}'
    arch_spec = spack.spec.Spec(
        arch_fmt.format(host_platform, host_os, host_target)
    )
    return {
        'target': str(host_target),
        'os': str(host_os),
        'platform': str(host_platform),
        'arch': arch_spec,
        'architecture': arch_spec,
        'arch_str': str(arch_spec),
        'hostname': socket.gethostname()
    }


@contextlib.contextmanager
def set_env(**kwargs):
    """Temporarily sets and restores environment variables.

    Variables can be set as keyword arguments to this function.
    """
    saved = {}
    for var, value in kwargs.items():
        if var in os.environ:
            saved[var] = os.environ[var]

        if value is None:
            if var in os.environ:
                del os.environ[var]
        else:
            os.environ[var] = value

    yield

    for var, value in kwargs.items():
        if var in saved:
            os.environ[var] = saved[var]
        else:
            if var in os.environ:
                del os.environ[var]


class NameModifier(object):

    def __init__(self, name, **kwargs):
        self.name = name
        self.separator = kwargs.get('separator', os.pathsep)
        self.args = {'name': name, 'separator': self.separator}

        self.args.update(kwargs)

    def __eq__(self, other):
        if not isinstance(other, NameModifier):
            return False
        return self.name == other.name

    def update_args(self, **kwargs):
        self.__dict__.update(kwargs)
        self.args.update(kwargs)


class NameValueModifier(object):

    def __init__(self, name, value, **kwargs):
        self.name = name
        self.value = value
        self.separator = kwargs.get('separator', os.pathsep)
        self.args = {'name': name, 'value': value, 'separator': self.separator}
        self.args.update(kwargs)

    def __eq__(self, other):
        if not isinstance(other, NameValueModifier):
            return False
        return self.name == other.name and \
            self.value == other.value and \
            self.separator == other.separator

    def update_args(self, **kwargs):
        self.__dict__.update(kwargs)
        self.args.update(kwargs)


class SetEnv(NameValueModifier):

    def execute(self, env):
        tty.debug("SetEnv: {0}={1}".format(self.name, str(self.value)),
                  level=3)
        env[self.name] = str(self.value)


class AppendFlagsEnv(NameValueModifier):

    def execute(self, env):
        tty.debug("AppendFlagsEnv: {0}={1}".format(self.name, str(self.value)),
                  level=3)
        if self.name in env and env[self.name]:
            env[self.name] += self.separator + str(self.value)
        else:
            env[self.name] = str(self.value)


class UnsetEnv(NameModifier):

    def execute(self, env):
        tty.debug("UnsetEnv: {0}".format(self.name), level=3)
        # Avoid throwing if the variable was not set
        env.pop(self.name, None)


class RemoveFlagsEnv(NameValueModifier):

    def execute(self, env):
        tty.debug("RemoveFlagsEnv: {0}-{1}".format(self.name, str(self.value)),
                  level=3)
        environment_value = env.get(self.name, '')
        flags = environment_value.split(
            self.separator) if environment_value else []
        flags = [f for f in flags if f != self.value]
        env[self.name] = self.separator.join(flags)


class SetPath(NameValueModifier):

    def execute(self, env):
        string_path = concatenate_paths(self.value, separator=self.separator)
        tty.debug("SetPath: {0}={1}".format(self.name, string_path), level=3)
        env[self.name] = string_path


class AppendPath(NameValueModifier):

    def execute(self, env):
        tty.debug("AppendPath: {0}+{1}".format(self.name, str(self.value)),
                  level=3)
        environment_value = env.get(self.name, '')
        directories = environment_value.split(
            self.separator) if environment_value else []
        directories.append(path_to_os_path(os.path.normpath(self.value)).pop())
        env[self.name] = self.separator.join(directories)


class PrependPath(NameValueModifier):

    def execute(self, env):
        tty.debug("PrependPath: {0}+{1}".format(self.name, str(self.value)),
                  level=3)
        environment_value = env.get(self.name, '')
        directories = environment_value.split(
            self.separator) if environment_value else []
        directories = [path_to_os_path(os.path.normpath(self.value)).pop()] \
            + directories
        env[self.name] = self.separator.join(directories)


class RemovePath(NameValueModifier):

    def execute(self, env):
        tty.debug("RemovePath: {0}-{1}".format(self.name, str(self.value)),
                  level=3)
        environment_value = env.get(self.name, '')
        directories = environment_value.split(
            self.separator) if environment_value else []
        directories = [path_to_os_path(os.path.normpath(x)).pop()
                       for x in directories
                       if x != path_to_os_path(os.path.normpath(self.value)).pop()]
        env[self.name] = self.separator.join(directories)


class DeprioritizeSystemPaths(NameModifier):

    def execute(self, env):
        tty.debug("DeprioritizeSystemPaths: {0}".format(self.name), level=3)
        environment_value = env.get(self.name, '')
        directories = environment_value.split(
            self.separator) if environment_value else []
        directories = deprioritize_system_paths(
            [path_to_os_path(os.path.normpath(x)).pop() for x in directories])
        env[self.name] = self.separator.join(directories)


class PruneDuplicatePaths(NameModifier):

    def execute(self, env):
        tty.debug("PruneDuplicatePaths: {0}".format(self.name),
                  level=3)
        environment_value = env.get(self.name, '')
        directories = environment_value.split(
            self.separator) if environment_value else []
        directories = prune_duplicate_paths([path_to_os_path(os.path.normpath(x)).pop()
                                             for x in directories])
        env[self.name] = self.separator.join(directories)


class EnvironmentModifications(object):
    """Keeps track of requests to modify the current environment.

    Each call to a method to modify the environment stores the extra
    information on the caller in the request:

        * 'filename' : filename of the module where the caller is defined
        * 'lineno': line number where the request occurred
        * 'context' : line of code that issued the request that failed
    """

    def __init__(self, other=None, traced=None):
        """Initializes a new instance, copying commands from 'other'
        if it is not None.

        Args:
            other (EnvironmentModifications): list of environment modifications
                to be extended (optional)
            traced (bool): enable or disable stack trace inspection to log the origin
                of the environment modifications.
        """
        self.traced = tracing_enabled if traced is None else bool(traced)
        self.env_modifications = []
        if other is not None:
            self.extend(other)

    def __iter__(self):
        return iter(self.env_modifications)

    def __len__(self):
        return len(self.env_modifications)

    def extend(self, other):
        self._check_other(other)
        self.env_modifications.extend(other.env_modifications)

    @staticmethod
    def _check_other(other):
        if not isinstance(other, EnvironmentModifications):
            raise TypeError(
                'other must be an instance of EnvironmentModifications')

    def _maybe_trace(self, kwargs):
        """Provide the modification with stack trace info so that we can track its
        origin to find issues in packages. This is very slow and expensive."""
        if not self.traced:
            return

        stack = inspect.stack()
        try:
            _, filename, lineno, _, context, index = stack[2]
            context = context[index].strip()
        except Exception:
            filename = 'unknown file'
            lineno = 'unknown line'
            context = 'unknown context'
        kwargs.update({'filename': filename, 'lineno': lineno, 'context': context})

    def set(self, name, value, **kwargs):
        """Stores a request to set an environment variable.

        Args:
            name: name of the environment variable to be set
            value: value of the environment variable
        """
        self._maybe_trace(kwargs)
        item = SetEnv(name, value, **kwargs)
        self.env_modifications.append(item)

    def append_flags(self, name, value, sep=' ', **kwargs):
        """
        Stores in the current object a request to append to an env variable

        Args:
            name: name of the environment variable to be appended to
            value: value to append to the environment variable
        Appends with spaces separating different additions to the variable
        """
        self._maybe_trace(kwargs)
        kwargs.update({'separator': sep})
        item = AppendFlagsEnv(name, value, **kwargs)
        self.env_modifications.append(item)

    def unset(self, name, **kwargs):
        """Stores a request to unset an environment variable.

        Args:
            name: name of the environment variable to be unset
        """
        self._maybe_trace(kwargs)
        item = UnsetEnv(name, **kwargs)
        self.env_modifications.append(item)

    def remove_flags(self, name, value, sep=' ', **kwargs):
        """
        Stores in the current object a request to remove flags from an
        env variable

        Args:
            name: name of the environment variable to be removed from
            value: value to remove to the environment variable
            sep: separator to assume for environment variable
        """
        self._maybe_trace(kwargs)
        kwargs.update({'separator': sep})
        item = RemoveFlagsEnv(name, value, **kwargs)
        self.env_modifications.append(item)

    def set_path(self, name, elements, **kwargs):
        """Stores a request to set a path generated from a list.

        Args:
            name: name o the environment variable to be set.
            elements: elements of the path to set.
        """
        self._maybe_trace(kwargs)
        item = SetPath(name, elements, **kwargs)
        self.env_modifications.append(item)

    def append_path(self, name, path, **kwargs):
        """Stores a request to append a path to a path list.

        Args:
            name: name of the path list in the environment
            path: path to be appended
        """
        self._maybe_trace(kwargs)
        item = AppendPath(name, path, **kwargs)
        self.env_modifications.append(item)

    def prepend_path(self, name, path, **kwargs):
        """Same as `append_path`, but the path is pre-pended.

        Args:
            name: name of the path list in the environment
            path: path to be pre-pended
        """
        self._maybe_trace(kwargs)
        item = PrependPath(name, path, **kwargs)
        self.env_modifications.append(item)

    def remove_path(self, name, path, **kwargs):
        """Stores a request to remove a path from a path list.

        Args:
            name: name of the path list in the environment
            path: path to be removed
        """
        self._maybe_trace(kwargs)
        item = RemovePath(name, path, **kwargs)
        self.env_modifications.append(item)

    def deprioritize_system_paths(self, name, **kwargs):
        """Stores a request to deprioritize system paths in a path list,
        otherwise preserving the order.

        Args:
            name: name of the path list in the environment.
        """
        self._maybe_trace(kwargs)
        item = DeprioritizeSystemPaths(name, **kwargs)
        self.env_modifications.append(item)

    def prune_duplicate_paths(self, name, **kwargs):
        """Stores a request to remove duplicates from a path list, otherwise
        preserving the order.

        Args:
            name: name of the path list in the environment.
        """
        self._maybe_trace(kwargs)
        item = PruneDuplicatePaths(name, **kwargs)
        self.env_modifications.append(item)

    def group_by_name(self):
        """Returns a dict of the modifications grouped by variable name.

        Returns:
            dict mapping the environment variable name to the modifications to
            be done on it
        """
        modifications = collections.defaultdict(list)
        for item in self:
            modifications[item.name].append(item)
        return modifications

    def is_unset(self, var_name):
        modifications = self.group_by_name()
        var_updates = modifications.get(var_name, None)
        if not var_updates:
            # We did not explicitly unset it
            return False

        # The last modification must unset the variable for it to be considered
        # unset
        return (type(var_updates[-1]) == UnsetEnv)

    def clear(self):
        """
        Clears the current list of modifications
        """
        self.env_modifications = []

    def reversed(self):
        """
        Returns the EnvironmentModifications object that will reverse self

        Only creates reversals for additions to the environment, as reversing
        ``unset`` and ``remove_path`` modifications is impossible.

        Reversable operations are set(), prepend_path(), append_path(),
        set_path(), and append_flags().
        """
        rev = EnvironmentModifications()

        for envmod in reversed(self.env_modifications):
            if type(envmod) == SetEnv:
                tty.debug("Reversing `Set` environment operation may lose "
                          "original value")
                rev.unset(envmod.name)
            elif type(envmod) == AppendPath:
                rev.remove_path(envmod.name, envmod.value)
            elif type(envmod) == PrependPath:
                rev.remove_path(envmod.name, envmod.value)
            elif type(envmod) == SetPath:
                tty.debug("Reversing `SetPath` environment operation may lose "
                          "original value")
                rev.unset(envmod.name)
            elif type(envmod) == AppendFlagsEnv:
                rev.remove_flags(envmod.name, envmod.value)
            else:
                # This is an un-reversable operation
                tty.warn("Skipping reversal of unreversable operation"
                         "%s %s" % (type(envmod), envmod.name))

        return rev

    def apply_modifications(self, env=None):
        """Applies the modifications and clears the list."""
        # Use os.environ if not specified
        # Do not copy, we want to modify it in place
        if env is None:
            env = os.environ

        modifications = self.group_by_name()
        # Apply modifications one variable at a time
        for name, actions in sorted(modifications.items()):
            for x in actions:
                x.execute(env)

    def shell_modifications(self, shell='sh', explicit=False, env=None):
        """Return shell code to apply the modifications and clears the list."""
        modifications = self.group_by_name()

        if env is None:
            env = os.environ

        new_env = env.copy()

        for name, actions in sorted(modifications.items()):
            for x in actions:
                x.execute(new_env)

        if 'MANPATH' in new_env and not new_env.get('MANPATH').endswith(':'):
            new_env['MANPATH'] += ':'

        cmds = ''

        for name in sorted(set(modifications)):
            new = new_env.get(name, None)
            old = env.get(name, None)
            if explicit or new != old:
                if new is None:
                    cmds += _shell_unset_strings[shell].format(name)
                else:
                    if sys.platform != "win32":
                        cmd = _shell_set_strings[shell].format(
                            name, cmd_quote(new_env[name]))
                    else:
                        cmd = _shell_set_strings[shell].format(
                            name, new_env[name])
                    cmds += cmd
        return cmds

    @staticmethod
    def from_sourcing_file(filename, *arguments, **kwargs):
        """Constructs an instance of a
        :py:class:`spack.util.environment.EnvironmentModifications` object
        that has the same effect as sourcing a file.

        Args:
            filename (str): the file to be sourced
            *arguments (list): arguments to pass on the command line

        Keyword Args:
            shell (str): the shell to use (default: ``bash``)
            shell_options (str): options passed to the shell (default: ``-c``)
            source_command (str): the command to run (default: ``source``)
            suppress_output (str): redirect used to suppress output of command
                (default: ``&> /dev/null``)
            concatenate_on_success (str): operator used to execute a command
                only when the previous command succeeds (default: ``&&``)
            blacklist ([str or re]): ignore any modifications of these
                variables (default: [])
            whitelist ([str or re]): always respect modifications of these
                variables (default: []). has precedence over blacklist.
            clean (bool): in addition to removing empty entries,
                also remove duplicate entries (default: False).
        """
        tty.debug("EnvironmentModifications.from_sourcing_file: {0}"
                  .format(filename))
        # Check if the file actually exists
        if not os.path.isfile(filename):
            msg = 'Trying to source non-existing file: {0}'.format(filename)
            raise RuntimeError(msg)

        # Prepare a whitelist and a blacklist of environment variable names
        blacklist = kwargs.get('blacklist', [])
        whitelist = kwargs.get('whitelist', [])
        clean = kwargs.get('clean', False)

        # Other variables unrelated to sourcing a file
        blacklist.extend([
            # Bash internals
            'SHLVL', '_', 'PWD', 'OLDPWD', 'PS1', 'PS2', 'ENV',
            # Environment modules v4
            'LOADEDMODULES', '_LMFILES_', 'BASH_FUNC_module()', 'MODULEPATH',
            'MODULES_(.*)', r'(\w*)_mod(quar|share)',
            # Lmod configuration
            r'LMOD_(.*)', 'MODULERCFILE'
        ])

        # Compute the environments before and after sourcing
        before = sanitize(
            environment_after_sourcing_files(os.devnull, **kwargs),
            blacklist=blacklist, whitelist=whitelist
        )
        file_and_args = (filename,) + arguments
        after = sanitize(
            environment_after_sourcing_files(file_and_args, **kwargs),
            blacklist=blacklist, whitelist=whitelist
        )

        # Delegate to the other factory
        return EnvironmentModifications.from_environment_diff(
            before, after, clean
        )

    @staticmethod
    def from_environment_diff(before, after, clean=False):
        """Constructs an instance of a
        :py:class:`spack.util.environment.EnvironmentModifications` object
        from the diff of two dictionaries.

        Args:
            before (dict): environment before the modifications are applied
            after (dict): environment after the modifications are applied
            clean (bool): in addition to removing empty entries, also remove
                duplicate entries
        """
        # Fill the EnvironmentModifications instance
        env = EnvironmentModifications()
        # New variables
        new_variables = list(set(after) - set(before))
        # Variables that have been unset
        unset_variables = list(set(before) - set(after))
        # Variables that have been modified
        common_variables = set(before).intersection(set(after))
        modified_variables = [x for x in common_variables
                              if before[x] != after[x]]
        # Consistent output order - looks nicer, easier comparison...
        new_variables.sort()
        unset_variables.sort()
        modified_variables.sort()

        def return_separator_if_any(*args):
            separators = ':', ';'
            for separator in separators:
                for arg in args:
                    if separator in arg:
                        return separator
            return None

        # Add variables to env.
        # Assume that variables with 'PATH' in the name or that contain
        # separators like ':' or ';' are more likely to be paths
        for x in new_variables:
            sep = return_separator_if_any(after[x])
            if sep:
                env.prepend_path(x, after[x], separator=sep)
            elif 'PATH' in x:
                env.prepend_path(x, after[x])
            else:
                # We just need to set the variable to the new value
                env.set(x, after[x])

        for x in unset_variables:
            env.unset(x)

        for x in modified_variables:
            value_before = before[x]
            value_after = after[x]
            sep = return_separator_if_any(value_before, value_after)
            if sep:
                before_list = value_before.split(sep)
                after_list = value_after.split(sep)

                # Filter out empty strings
                before_list = list(filter(None, before_list))
                after_list = list(filter(None, after_list))

                # Remove duplicate entries (worse matching, bloats env)
                if clean:
                    before_list = list(dedupe(before_list))
                    after_list = list(dedupe(after_list))
                    # The reassembled cleaned entries
                    value_before = sep.join(before_list)
                    value_after = sep.join(after_list)

                # Paths that have been removed
                remove_list = [
                    ii for ii in before_list if ii not in after_list]
                # Check that nothing has been added in the middle of
                # before_list
                remaining_list = [
                    ii for ii in before_list if ii in after_list]
                try:
                    start = after_list.index(remaining_list[0])
                    end = after_list.index(remaining_list[-1])
                    search = sep.join(after_list[start:end + 1])
                except IndexError:
                    env.prepend_path(x, value_after)
                    continue

                if search not in value_before:
                    # We just need to set the variable to the new value
                    env.prepend_path(x, value_after)
                else:
                    try:
                        prepend_list = after_list[:start]
                        prepend_list.reverse()  # Preserve order after prepend
                    except KeyError:
                        prepend_list = []
                    try:
                        append_list = after_list[end + 1:]
                    except KeyError:
                        append_list = []

                    for item in remove_list:
                        env.remove_path(x, item)
                    for item in append_list:
                        env.append_path(x, item)
                    for item in prepend_list:
                        env.prepend_path(x, item)
            else:
                # We just need to set the variable to the new value
                env.set(x, value_after)

        return env


def concatenate_paths(paths, separator=os.pathsep):
    """Concatenates an iterable of paths into a string of paths separated by
    separator, defaulting to colon.

    Args:
        paths: iterable of paths
        separator: the separator to use, default ';' windows, ':' otherwise

    Returns:
        string
    """
    return separator.join(str(item) for item in paths)


def set_or_unset_not_first(variable, changes, errstream):
    """Check if we are going to set or unset something after other
    modifications have already been requested.
    """
    indexes = [ii for ii, item in enumerate(changes)
               if ii != 0 and
               not item.args.get('force', False) and
               type(item) in [SetEnv, UnsetEnv]]
    if indexes:
        good = '\t    \t{context} at {filename}:{lineno}'
        nogood = '\t--->\t{context} at {filename}:{lineno}'
        message = "Suspicious requests to set or unset '{var}' found"
        errstream(message.format(var=variable))
        for ii, item in enumerate(changes):
            print_format = nogood if ii in indexes else good
            errstream(print_format.format(**item.args))


def validate(env, errstream):
    """Validates the environment modifications to check for the presence of
    suspicious patterns. Prompts a warning for everything that was found.

    Current checks:
    - set or unset variables after other changes on the same variable

    Args:
        env: list of environment modifications
    """
    if not env.traced:
        return
    modifications = env.group_by_name()
    for variable, list_of_changes in sorted(modifications.items()):
        set_or_unset_not_first(variable, list_of_changes, errstream)


def filter_environment_blacklist(env, variables):
    """Generator that filters out any change to environment variables present in
    the input list.

    Args:
        env: list of environment modifications
        variables: list of variable names to be filtered

    Returns:
        items in env if they are not in variables
    """
    for item in env:
        if item.name not in variables:
            yield item


def inspect_path(root, inspections, exclude=None):
    """Inspects ``root`` to search for the subdirectories in ``inspections``.
    Adds every path found to a list of prepend-path commands and returns it.

    Args:
        root (str): absolute path where to search for subdirectories

        inspections (dict): maps relative paths to a list of environment
            variables that will be modified if the path exists. The
            modifications are not performed immediately, but stored in a
            command object that is returned to client

        exclude (typing.Callable): optional callable. If present it must accept an
            absolute path and return True if it should be excluded from the
            inspection

    Examples:

    The following lines execute an inspection in ``/usr`` to search for
    ``/usr/include`` and ``/usr/lib64``. If found we want to prepend
    ``/usr/include`` to ``CPATH`` and ``/usr/lib64`` to ``MY_LIB64_PATH``.

        .. code-block:: python

            # Set up the dictionary containing the inspection
            inspections = {
                'include': ['CPATH'],
                'lib64': ['MY_LIB64_PATH']
            }

            # Get back the list of command needed to modify the environment
            env = inspect_path('/usr', inspections)

            # Eventually execute the commands
            env.apply_modifications()

    Returns:
        instance of EnvironmentModifications containing the requested
        modifications
    """
    if exclude is None:
        exclude = lambda x: False

    env = EnvironmentModifications()
    # Inspect the prefix to check for the existence of common directories
    for relative_path, variables in inspections.items():
        expected = os.path.join(root, relative_path)

        if os.path.isdir(expected) and not exclude(expected):
            for variable in variables:
                env.prepend_path(variable, expected)

    return env


@contextlib.contextmanager
def preserve_environment(*variables):
    """Ensures that the value of the environment variables passed as
    arguments is the same before entering to the context manager and after
    exiting it.

    Variables that are unset before entering the context manager will be
    explicitly unset on exit.

    Args:
        variables (list): list of environment variables to be preserved
    """
    cache = {}
    for var in variables:
        # The environment variable to be preserved might not be there.
        # In that case store None as a placeholder.
        cache[var] = os.environ.get(var, None)

    yield

    for var in variables:
        value = cache[var]
        msg = '[PRESERVE_ENVIRONMENT]'
        if value is not None:
            # Print a debug statement if the value changed
            if var not in os.environ:
                msg += ' {0} was unset, will be reset to "{1}"'
                tty.debug(msg.format(var, value))
            elif os.environ[var] != value:
                msg += ' {0} was set to "{1}", will be reset to "{2}"'
                tty.debug(msg.format(var, os.environ[var], value))
            os.environ[var] = value
        elif var in os.environ:
            msg += ' {0} was set to "{1}", will be unset'
            tty.debug(msg.format(var, os.environ[var]))
            del os.environ[var]


def environment_after_sourcing_files(*files, **kwargs):
    """Returns a dictionary with the environment that one would have
    after sourcing the files passed as argument.

    Args:
        *files: each item can either be a string containing the path
            of the file to be sourced or a sequence, where the first element
            is the file to be sourced and the remaining are arguments to be
            passed to the command line

    Keyword Args:
        env (dict): the initial environment (default: current environment)
        shell (str): the shell to use (default: ``/bin/bash``)
        shell_options (str): options passed to the shell (default: ``-c``)
        source_command (str): the command to run (default: ``source``)
        suppress_output (str): redirect used to suppress output of command
            (default: ``&> /dev/null``)
        concatenate_on_success (str): operator used to execute a command
            only when the previous command succeeds (default: ``&&``)
    """
    # Set the shell executable that will be used to source files
    shell_cmd = kwargs.get('shell', '/bin/bash')
    shell_options = kwargs.get('shell_options', '-c')
    source_command = kwargs.get('source_command', 'source')
    suppress_output = kwargs.get('suppress_output', '&> /dev/null')
    concatenate_on_success = kwargs.get('concatenate_on_success', '&&')

    shell = executable.Executable(' '.join([shell_cmd, shell_options]))

    def _source_single_file(file_and_args, environment):
        source_file = [source_command]
        source_file.extend(x for x in file_and_args)
        source_file = ' '.join(source_file)

        # If the environment contains 'python' use it, if not
        # go with sys.executable. Below we just need a working
        # Python interpreter, not necessarily sys.executable.
        python_cmd = executable.which('python3', 'python', 'python2')
        python_cmd = python_cmd.path if python_cmd else sys.executable

        dump_cmd = 'import os, json; print(json.dumps(dict(os.environ)))'
        dump_environment = python_cmd + ' -E -c "{0}"'.format(dump_cmd)

        # Try to source the file
        source_file_arguments = ' '.join([
            source_file, suppress_output,
            concatenate_on_success, dump_environment,
        ])
        output = shell(
            source_file_arguments, output=str, env=environment, ignore_quotes=True
        )
        environment = json.loads(output)

        # If we're in python2, convert to str objects instead of unicode
        # like json gives us.  We can't put unicode in os.environ anyway.
        return sjson.encode_json_dict(environment)

    current_environment = kwargs.get('env', dict(os.environ))
    for f in files:
        # Normalize the input to the helper function
        if isinstance(f, six.string_types):
            f = [f]

        current_environment = _source_single_file(
            f, environment=current_environment
        )

    return current_environment


def sanitize(environment, blacklist, whitelist):
    """Returns a copy of the input dictionary where all the keys that
    match a blacklist pattern and don't match a whitelist pattern are
    removed.

    Args:
        environment (dict): input dictionary
        blacklist (list): literals or regex patterns to be
            blacklisted
        whitelist (list): literals or regex patterns to be
            whitelisted
    """

    def set_intersection(fullset, *args):
        # A set intersection using string literals and regexs
        meta = '[' + re.escape('[$()*?[]^{|}') + ']'
        subset = fullset & set(args)  # As literal
        for name in args:
            if re.search(meta, name):
                pattern = re.compile(name)
                for k in fullset:
                    if re.match(pattern, k):
                        subset.add(k)
        return subset

    # Don't modify input, make a copy instead
    environment = sjson.decode_json_dict(dict(environment))

    # Retain (whitelist) has priority over prune (blacklist)
    prune = set_intersection(set(environment), *blacklist)
    prune -= set_intersection(prune, *whitelist)
    for k in prune:
        environment.pop(k, None)

    return environment
