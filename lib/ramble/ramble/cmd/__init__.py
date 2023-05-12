# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from __future__ import print_function

import os
import re
import argparse
import ruamel.yaml as yaml

import llnl.util.tty as tty
from llnl.util.lang import attr_setdefault
from llnl.util.filesystem import join_path

import ramble.config
import ramble.error
import ramble.paths
import ramble.workspace

import spack.extensions
import spack.util.string

from ruamel.yaml.error import MarkedYAMLError

# cmd has a submodule called "list" so preserve the python list module
python_list = list

# Patterns to ignore in the commands directory when looking for commands.
ignore_files = r'^\.|^__init__.py$|^#'

SETUP_PARSER = "setup_parser"
DESCRIPTION = "description"


def python_name(cmd_name):
    """Convert ``-`` to ``_`` in command name, to make a valid identifier."""
    return cmd_name.replace("-", "_")


def require_python_name(pname):
    """Require that the provided name is a valid python name (per
    python_name()). Useful for checking parameters for function
    prerequisites."""
    if python_name(pname) != pname:
        raise PythonNameError(pname)


def cmd_name(python_name):
    """Convert module name (with ``_``) to command name (with ``-``)."""
    return python_name.replace('_', '-')


def require_cmd_name(cname):
    """Require that the provided name is a valid command name (per
    cmd_name()). Useful for checking parameters for function
    prerequisites.
    """
    if cmd_name(cname) != cname:
        raise CommandNameError(cname)


#: global, cached list of all commands -- access through all_commands()
_all_commands = None


def all_commands():
    """Get a sorted list of all ramble commands.

    This will list the lib/ramble/ramble/cmd directory and find the
    commands there to construct the list.  It does not actually import
    the python files -- just gets the names.
    """
    global _all_commands
    if _all_commands is None:
        _all_commands = []
        command_paths = [ramble.paths.command_path]  # Built-in commands
        for path in command_paths:
            for file in os.listdir(path):
                if file.endswith(".py") and not re.search(ignore_files, file):
                    cmd = re.sub(r'.py$', '', file)
                    _all_commands.append(cmd_name(cmd))

        _all_commands.sort()

    return _all_commands


def remove_options(parser, *options):
    """Remove some options from a parser."""
    for option in options:
        for action in parser._actions:
            if vars(action)['option_strings'][0] == option:
                parser._handle_conflict_resolve(None, [(option, action)])
                break


def get_module(cmd_name):
    """Imports the module for a particular command name and returns it.

    Args:
        cmd_name (str): name of the command for which to get a module
            (contains ``-``, not ``_``).
    """
    require_cmd_name(cmd_name)
    pname = python_name(cmd_name)

    tty.debug('Getting module for command {}'.format(cmd_name))

    try:
        # Try to import the command from the built-in directory
        module_name = "%s.%s" % (__name__, pname)
        module = __import__(module_name,
                            fromlist=[pname, SETUP_PARSER, DESCRIPTION],
                            level=0)
        tty.debug('Imported {0} from built-in commands'.format(pname))
    except ImportError:
        try:
            module = spack.extensions.get_module(cmd_name)
        except AttributeError:
            from ramble.main import RambleCommandError
            raise RambleCommandError('Command %s does not exist.' % cmd_name)

    attr_setdefault(module, SETUP_PARSER, lambda *args: None)  # null-op
    attr_setdefault(module, DESCRIPTION, "")

    if not hasattr(module, pname):
        tty.die("Command module %s (%s) must define function '%s'." %
                (module.__name__, module.__file__, pname))

    return module


def get_command(cmd_name):
    """Imports the command function associated with cmd_name.

    The function's name is derived from cmd_name using python_name().

    Args:
        cmd_name (str): name of the command (contains ``-``, not ``_``).
    """
    require_cmd_name(cmd_name)
    pname = python_name(cmd_name)
    return getattr(get_module(cmd_name), pname)


def elide_list(line_list, max_num=10):
    """Takes a long list and limits it to a smaller number of elements,
       replacing intervening elements with '...'.  For example::

           elide_list([1,2,3,4,5,6], 4)

       gives::

           [1, 2, 3, '...', 6]
    """
    if len(line_list) > max_num:
        return line_list[:max_num - 1] + ['...'] + line_list[-1:]
    else:
        return line_list


def ramble_is_git_repo():
    """Ensure that this instance of Ramble is a git clone."""
    return is_git_repo(ramble.paths.prefix)


def is_git_repo(path):
    dotgit_path = join_path(path, '.git')
    if os.path.isdir(dotgit_path):
        # we are in a regular git repo
        return True
    if os.path.isfile(dotgit_path):
        # we might be in a git worktree
        try:
            with open(dotgit_path, "rb") as f:
                dotgit_content = yaml.load(f)
            return os.path.isdir(dotgit_content.get("gitdir", dotgit_path))
        except MarkedYAMLError:
            pass
    return False


class PythonNameError(ramble.error.RambleError):
    """Exception class thrown for impermissible python names"""
    def __init__(self, name):
        self.name = name
        super(PythonNameError, self).__init__(
            '{0} is not a permissible Python name.'.format(name))


class CommandNameError(ramble.error.RambleError):
    """Exception class thrown for impermissible command names"""
    def __init__(self, name):
        self.name = name
        super(CommandNameError, self).__init__(
            '{0} is not a permissible Ramble command name.'.format(name))


########################################
# argparse types for argument validation
########################################
def extant_file(f):
    """
    Argparse type for files that exist.
    """
    if not os.path.isfile(f):
        raise argparse.ArgumentTypeError('%s does not exist' % f)
    return f


def require_active_workspace(cmd_name):
    """Used by commands to get the active workspace

    If a workspace is not found, print an error message that says the calling
    command *needs* an active workspace.

    Arguments:
        cmd_name (str): name of calling command

    Returns:
        (ramble.workspace.Workspace): the active workspace
    """
    ws = ramble.workspace.active_workspace()

    if ws:
        return ws
    else:
        tty.die(
            '`ramble %s` requires a workspace' % cmd_name,
            'activate a workspace first:',
            '    ramble workspace activate WRKSPC',
            'or use:',
            '    ramble -w WRKSPC %s ...' % cmd_name)


def find_workspace(args):
    """Find active workspace from args or environment variable.

    Check for a workspace in this order:
        1. via ``ramble -w WRKSPC`` or ``ramble -D DIR`` (arguments)
        2. via a path in the ramble.workspace.ramble_workspace_var environment variable.

    If a workspace is found, read it in.  If not, return None.

    Arguments:
        args (argparse.Namespace): argparse namespace with command arguments

    Returns:
        (ramble.workspace.Workspace): a found workspace, or ``None``
    """

    # treat workspace as a name
    ws = args.workspace
    if ws:
        if ramble.workspace.exists(ws):
            return ramble.workspace.read(ws)

    else:
        # if workspace was specified, see if it is a directory otherwise, look
        # at workspace_dir (workspace and workspace_dir are mutually exclusive)
        ws = args.workspace_dir

        # if no argument, look for the environment variable
        if not ws:
            ws = os.environ.get(ramble.workspace.ramble_workspace_var)

            # nothing was set; there's no active environment
            if not ws:
                return None

    # if we get here, env isn't the name of a spack environment; it has
    # to be a path to an environment, or there is something wrong.
    if ramble.workspace.is_workspace_dir(ws):
        return ramble.workspace.Workspace(ws)

    raise ramble.workspace.RambleWorkspaceError('no workspace in %s' % ws)


def find_workspace_path(args):
    """Find path to active workspace from args or environment variable.

    Check for a workspace in this order:
        1. via ``ramble -w WRKSPC`` or ``ramble -D DIR`` (arguments)
        2. via a path in the ramble.workspace.ramble_workspace_var environment variable.

    If a workspace is found, return it's path.  If not, return None.

    Arguments:
        args (argparse.Namespace): argparse namespace with command arguments

    Returns:
        (string): Path to workspace root, or None
    """

    # treat workspace as a name
    ws = args.workspace
    if ws:
        if ramble.workspace.exists(ws):
            return ramble.workspace.root(ws)

    else:
        # if workspace was specified, see if it is a directory otherwise, look
        # at workspace_dir (workspace and workspace_dir are mutually exclusive)
        ws = args.workspace_dir

        # if no argument, look for the environment variable
        if not ws:
            ws = os.environ.get(ramble.workspace.ramble_workspace_var)

            # nothing was set; there's no active environment
            if not ws:
                return None

    # if we get here, env isn't the name of a spack environment; it has
    # to be a path to an environment, or there is something wrong.
    if ramble.workspace.is_workspace_dir(ws):
        return ws

    raise ramble.workspace.RambleWorkspaceError('no workspace in %s' % ws)
