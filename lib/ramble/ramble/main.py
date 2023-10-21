# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""This is the implementation of the Ramble command line executable.

In a normal Ramble installation, this is invoked from the bin/ramble script
after the system path is set up.
"""
from __future__ import print_function

import argparse
import inspect
import operator
import os
import os.path
import pstats
import re
import signal
import sys
import traceback
import warnings
import jsonschema
import ruamel

from six import StringIO

import llnl.util.lang
import llnl.util.tty as tty
import llnl.util.tty.colify
import llnl.util.tty.color as color
from llnl.util.tty.log import log_output

import ramble
import ramble.cmd
import ramble.config
import ramble.workspace
import ramble.workspace.shell
import ramble.paths
import ramble.repository
import spack.util.debug
import spack.util.environment
import spack.util.path
from ramble.error import RambleError

#: names of profile statistics
stat_names = pstats.Stats.sort_arg_dict_default

#: top-level aliases for Ramble commands
aliases = {
    'rm': 'remove'
}

#: help levels in order of detail (i.e., number of commands shown)
levels = ['short', 'long']

#: intro text for help at different levels
intro_by_level = {
    'short': 'These are common ramble commands:',
    'long':  'Complete list of ramble commands:',
}

#: control top-level ramble options shown in basic vs. advanced help
options_by_level = {
    'short': ['h', 'k', 'V', 'color'],
    'long': 'all'
}

#: Longer text for each section, to show in help
section_descriptions = {
    'admin':       'administration',
    'basic':       'query applications',
    'config':      'configuration',
    'developer':   'developer',
    'help':        'more help',
    'system':      'system',
}

#: preferential command order for some sections (e.g., build pipeline is
#: in execution order, not alphabetical)
section_order = {
    'basic': ['list', 'info', 'find'],
}

#: Properties that commands are required to set.
required_command_properties = ['level', 'section', 'description']

#: Recorded directory where ramble command was originally invoked
ramble_working_dir = None
ramble_ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')


def set_working_dir():
    """Change the working directory to getcwd, or ramble prefix if no cwd."""
    global ramble_working_dir
    try:
        ramble_working_dir = os.getcwd()
    except OSError:
        os.chdir(ramble.paths.prefix)
        ramble_working_dir = ramble.paths.prefix


def add_all_commands(parser):
    """Add all ramble subcommands to the parser."""
    for cmd in ramble.cmd.all_commands():
        parser.add_command(cmd)


def get_version():
    """Get a descriptive version of this instance of Ramble.

    Outputs '<PEP440 version> (<git commit sha>)'.

    The commit sha is only added when available.
    """
    version = ramble.ramble_version
    git_hash = get_git_hash(path=ramble.paths.prefix)

    if git_hash:
        version += f' ({git_hash})'

    return version


def get_git_hash(path=ramble.paths.prefix):
    """Get get hash from a path

    Outputs '<git commit sha>'.
    """
    import spack.util.git
    git_path = os.path.join(path, ".git")
    if os.path.exists(git_path):
        git = spack.util.git.git()
        if not git:
            return
        rev = git(
            "-C",
            path,
            "rev-parse",
            "HEAD",
            output=str,
            error=os.devnull,
            fail_on_error=False,
        )
        if git.returncode != 0:
            return
        match = re.match(r"[a-f\d]{7,}$", rev)
        if match:
            return match.group(0)

    return


def index_commands():
    """create an index of commands by section for this help level"""
    index = {}
    for command in ramble.cmd.all_commands():
        cmd_module = ramble.cmd.get_module(command)

        # make sure command modules have required properties
        for p in required_command_properties:
            prop = getattr(cmd_module, p, None)
            if not prop:
                tty.die("Command doesn't define a property '%s': %s"
                        % (p, command))

        # add commands to lists for their level and higher levels
        for level in reversed(levels):
            level_sections = index.setdefault(level, {})
            commands = level_sections.setdefault(cmd_module.section, [])
            commands.append(command)
            if level == cmd_module.level:
                break

    return index


class RambleHelpFormatter(argparse.RawTextHelpFormatter):
    def _format_actions_usage(self, actions, groups):
        """Formatter with more concise usage strings."""
        usage = super(
            RambleHelpFormatter, self)._format_actions_usage(actions, groups)

        # Eliminate any occurrence of two or more consecutive spaces
        usage = re.sub(r'[ ]{2,}', ' ', usage)

        # compress single-character flags that are not mutually exclusive
        # at the beginning of the usage string
        chars = ''.join(re.findall(r'\[-(.)\]', usage))
        usage = re.sub(r'\[-.\] ?', '', usage)
        if chars:
            usage = '[-%s] %s' % (chars, usage)
        return usage.strip()

    def add_arguments(self, actions):
        actions = sorted(actions, key=operator.attrgetter('option_strings'))
        super(RambleHelpFormatter, self).add_arguments(actions)


class RambleArgumentParser(argparse.ArgumentParser):
    def format_help_sections(self, level):
        """Format help on sections for a particular verbosity level.

        Args:
            level (str): 'short' or 'long' (more commands shown for long)
        """
        if level not in levels:
            raise ValueError("level must be one of: %s" % levels)

        # lazily add all commands to the parser when needed.
        add_all_commands(self)

        """Print help on subcommands in neatly formatted sections."""
        formatter = self._get_formatter()

        # Create a list of subcommand actions. Argparse internals are nasty!
        # Note: you can only call _get_subactions() once.  Even nastier!
        if not hasattr(self, 'actions'):
            self.actions = self._subparsers._actions[-1]._get_subactions()

        # make a set of commands not yet added.
        remaining = set(ramble.cmd.all_commands())

        def add_group(group):
            formatter.start_section(group.title)
            formatter.add_text(group.description)
            formatter.add_arguments(group._group_actions)
            formatter.end_section()

        def add_subcommand_group(title, commands):
            """Add informational help group for a specific subcommand set."""
            cmd_set = set(c for c in commands)

            # make a dict of commands of interest
            cmds = dict((a.dest, a) for a in self.actions
                        if a.dest in cmd_set)

            # add commands to a group in order, and add the group
            group = argparse._ArgumentGroup(self, title=title)
            for name in commands:
                group._add_action(cmds[name])
                if name in remaining:
                    remaining.remove(name)
            add_group(group)

        # select only the options for the particular level we're showing.
        show_options = options_by_level[level]
        if show_options != 'all':
            opts = dict((opt.option_strings[0].strip('-'), opt)
                        for opt in self._optionals._group_actions)

            new_actions = [opts[letter] for letter in show_options]
            self._optionals._group_actions = new_actions

        # custom, more concise usage for top level
        help_options = self._optionals._group_actions
        help_options = help_options + [self._positionals._group_actions[-1]]
        formatter.add_usage(
            self.usage, help_options, self._mutually_exclusive_groups)

        # description
        formatter.add_text(self.description)

        # start subcommands
        formatter.add_text(intro_by_level[level])

        # add argument groups based on metadata in commands
        index = index_commands()
        sections = index[level]

        for section in sorted(sections):
            if section == 'help' or section == 'secret':
                continue   # Cover help in the epilog.

            group_description = section_descriptions.get(section, section)

            to_display = sections[section]
            commands = []

            # add commands whose order we care about first.
            if section in section_order:
                commands.extend(cmd for cmd in section_order[section]
                                if cmd in to_display)

            # add rest in alphabetical order.
            commands.extend(cmd for cmd in sorted(sections[section])
                            if cmd not in commands)

            # add the group to the parser
            add_subcommand_group(group_description, commands)

        # optionals
        add_group(self._optionals)

        # epilog
        formatter.add_text("""\
{help}:
  ramble help --all       list all commands and options
  ramble help <command>   help on a specific command
  ramble help --spec      help on the application specification syntax
  ramble docs             open https://ramble.rtfd.io/ in a browser
""".format(help=section_descriptions['help']))

        # determine help from format above
        return formatter.format_help()

    def add_subparsers(self, **kwargs):
        """Ensure that sensible defaults are propagated to subparsers"""
        kwargs.setdefault('metavar', 'SUBCOMMAND')

        # From Python 3.7 we can require a subparser, earlier versions
        # of argparse will error because required=True is unknown
        if sys.version_info[:2] > (3, 6):
            kwargs.setdefault('required', True)

        sp = super(RambleArgumentParser, self).add_subparsers(**kwargs)
        # This monkey patching is needed for Python 3.5 and 3.6, which support
        # having a required subparser but don't expose the API used above
        if sys.version_info[:2] == (3, 5) or sys.version_info[:2] == (3, 6):
            sp.required = True

        old_add_parser = sp.add_parser

        def add_parser(name, **kwargs):
            kwargs.setdefault('formatter_class', RambleHelpFormatter)
            return old_add_parser(name, **kwargs)
        sp.add_parser = add_parser
        return sp

    def add_command(self, cmd_name):
        """Add one subcommand to this parser."""
        # lazily initialize any subparsers
        if not hasattr(self, 'subparsers'):
            # remove the dummy "command" argument.
            if self._actions[-1].dest == 'command':
                self._remove_action(self._actions[-1])
            self.subparsers = self.add_subparsers(metavar='COMMAND',
                                                  dest="command")

        # each command module implements a parser() function, to which we
        # pass its subparser for setup.
        module = ramble.cmd.get_module(cmd_name)

        # build a list of aliases
        alias_list = [k for k, v in aliases.items() if v == cmd_name]

        subparser = self.subparsers.add_parser(
            cmd_name, aliases=alias_list,
            help=module.description, description=module.description)
        module.setup_parser(subparser)

        # return the callable function for the command
        return ramble.cmd.get_command(cmd_name)

    def format_help(self, level='short'):
        if self.prog == 'ramble':
            # use format_help_sections for the main ramble parser, but not
            # for subparsers
            return self.format_help_sections(level)
        else:
            # in subparsers, self.prog is, e.g., 'ramble list'
            return super(RambleArgumentParser, self).format_help()

    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            cols = llnl.util.tty.colify.colified(
                sorted(action.choices), indent=4, tty=True
            )
            msg = 'invalid choice: %r choose from:\n%s' % (value, cols)
            raise argparse.ArgumentError(action, msg)


def make_argument_parser(**kwargs):
    """Create an basic argument parser without any subcommands added."""
    parser = RambleArgumentParser(
        formatter_class=RambleHelpFormatter, add_help=False,
        description=(
            "A flexible benchmark experiment manager."),
        **kwargs)

    # stat names in groups of 7, for nice wrapping.
    stat_lines = list(zip(*(iter(stat_names),) * 7))

    parser.add_argument(
        '-h', '--help',
        dest='help', action='store_const', const='short', default=None,
        help="show this help message and exit")
    parser.add_argument(
        '-H', '--all-help',
        dest='help', action='store_const', const='long', default=None,
        help="show help for all commands (same as ramble help --all)")
    parser.add_argument(
        '--color', action='store',
        default=os.environ.get('RAMBLE_COLOR', 'auto'),
        choices=('always', 'never', 'auto'),
        help="when to colorize output (default: auto)")
    parser.add_argument(
        '-c', '--config', default=None, action="append", dest="config_vars",
        help="add one or more custom, one off config settings.")
    parser.add_argument(
        '-C', '--config-scope', dest='config_scopes', action='append',
        metavar='DIR', help="add a custom configuration scope")
    parser.add_argument(
        '-d', '--debug', action='count', default=0,
        help="write out debug messages "
             "(more d's for more verbosity: -d, -dd, -ddd, etc.)")
    parser.add_argument(
        '--disable-passthrough', action='store_true',
        help="disable passthrough of expansion variables for debugging")
    parser.add_argument(
        '--timestamp', action='store_true',
        help="Add a timestamp to tty output")
    parser.add_argument(
        '--pdb', action='store_true',
        help="run ramble under the pdb debugger")

    workspace_group = parser.add_mutually_exclusive_group()
    workspace_group.add_argument(
        '-w', '--workspace', dest='workspace', metavar='WRKSPC', action='store',
        help="run with a specific workspace (see ramble workspace)")
    workspace_group.add_argument(
        '-D', '--workspace-dir', dest='workspace_dir', metavar='DIR', action='store',
        help="run with a workspace directory (ignore named workspaces)")
    workspace_group.add_argument(
        '-W', '--no-workspace', dest='no_workspace', action='store_true',
        help="run without any workspaces activated (see ramble workspace)")
    parser.add_argument(
        '--use-workspace-repo', action='store_true',
        help="when running in a workspace, use its application repository")

    parser.add_argument(
        '-k', '--insecure', action='store_true',
        help="do not check ssl certificates when downloading")
    parser.add_argument(
        '-l', '--enable-locks', action='store_true', dest='locks',
        default=None, help="use filesystem locking (default)")
    parser.add_argument(
        '-L', '--disable-locks', action='store_false', dest='locks',
        help="do not use filesystem locking (unsafe)")
    parser.add_argument(
        '-m', '--mock', action='store_true',
        help="use mock applications instead of real ones")
    # TODO (dwj): Do we need this?
    # parser.add_argument(
    #   # '-b', '--bootstrap', action='store_true',
    #   # help="use bootstrap configuration (bootstrap store, config, externals)")
    parser.add_argument(
        '-p', '--profile', action='store_true', dest='ramble_profile',
        help="profile execution using cProfile")
    parser.add_argument(
        '--sorted-profile', default=None, metavar="STAT",
        help="profile and sort by one or more of:\n[%s]" %
        ',\n '.join([', '.join(line) for line in stat_lines]))
    parser.add_argument(
        '--lines', default=20, action='store',
        help="lines of profile output or 'all' (default: 20)")
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help="print additional output during builds")
    parser.add_argument(
        '--stacktrace', action='store_true',
        default='RAMBLE_STACKTRACE' in os.environ,
        help="add stacktraces to all printed statements")
    parser.add_argument(
        '-V', '--version', action='store_true',
        help='show version number and exit')
    parser.add_argument(
        '--print-shell-vars', action='store',
        help="print info needed by setup-env.[c]sh")

    return parser


def send_warning_to_tty(message, *args):
    """Redirects messages to tty.warn."""
    tty.warn(message)


def setup_main_options(args):
    """Configure ramble globals based on the basic options."""
    # Assign a custom function to show warnings
    warnings.showwarning = send_warning_to_tty

    # Set up environment based on args.
    tty.set_verbose(args.verbose)
    tty.set_debug(args.debug)
    tty.set_stacktrace(args.stacktrace)

    # debug must be set first so that it can even affect behavior of
    # errors raised by ramble.config.

    if args.debug:
        ramble.error.debug = args.debug
        spack.util.debug.register_interrupt_handler()
        ramble.config.set('config:debug', True, scope='command_line')
        spack.util.environment.tracing_enabled = True

    if args.timestamp:
        tty.set_timestamp(True)

    # override lock configuration if passed on command line
    if args.locks is not None:
        if args.locks is False:
            spack.util.lock.check_lock_safety(ramble.paths.prefix)
        ramble.config.set('config:locks', args.locks, scope='command_line')

    # override disable_passthrough configuration if passed on command line
    if args.disable_passthrough:
        ramble.config.set('config:disable_passthrough', True, scope='command_line')

    if args.mock:
        import spack.util.spack_yaml as syaml

        for obj in ramble.repository.ObjectTypes:
            obj_section = ramble.repository.type_definitions[obj]['config_section']
            key = syaml.syaml_str(obj_section)
            key.override = True

            ramble.config.config.scopes["command_line"].sections[obj_section] = syaml.syaml_dict(
                [(key, [ramble.paths.mock_builtin_path])]
            )

            ramble.repository.paths[obj] = \
                ramble.repository.create(ramble.config.config, object_type=obj)

    # If the user asked for it, don't check ssl certs.
    if args.insecure:
        tty.warn("You asked for --insecure. Will NOT check SSL certificates.")
        ramble.config.set('config:verify_ssl', False, scope='command_line')

    # Use the ramble config command to handle parsing the config strings
    for config_var in (args.config_vars or []):
        ramble.config.add(fullpath=config_var, scope="command_line")

    # when to use color (takes always, auto, or never)
    color.set_color_when(args.color)


def allows_unknown_args(command):
    """Implements really simple argument injection for unknown arguments.

    Commands may add an optional argument called "unknown args" to
    indicate they can handle unknown args, and we'll pass the unknown
    args in.
    """
    info = dict(inspect.getmembers(command))
    varnames = info['__code__'].co_varnames
    argcount = info['__code__'].co_argcount
    return (argcount == 3 and varnames[2] == 'unknown_args')


def _invoke_command(command, parser, args, unknown_args):
    """Run a ramble command *without* setting ramble global options."""
    if allows_unknown_args(command):
        return_val = command(parser, args, unknown_args)
    else:
        if unknown_args:
            tty.die('unrecognized arguments: %s' % ' '.join(unknown_args))
        return_val = command(parser, args)

    # Allow commands to return and error code if they want
    return 0 if return_val is None else return_val


class RambleCommand(object):
    """Callable object that invokes a ramble command (for testing).

    Example usage::

        list = RambleCommand('list')
        list('hostname')

    Use this to invoke Ramble commands directly from Python and check
    their output.
    """
    def __init__(self, command_name):
        """Create a new RambleCommand that invokes ``command_name`` when called.

        Args:
            command_name (str): name of the command to invoke
        """
        self.parser = make_argument_parser()
        self.command = self.parser.add_command(command_name)
        self.command_name = command_name

    def __call__(self, *argv, **kwargs):
        """Invoke this RambleCommand.

        Args:
            argv (list): command line arguments.

        Keyword Args:
            fail_on_error (optional bool): Don't raise an exception on error
            global_args (optional list): List of global ramble arguments:
                simulates ``ramble [global_args] [command] [*argv]``

        Returns:
            (str): combined output and error as a string

        On return, if ``fail_on_error`` is False, return value of command
        is set in ``returncode`` property, and the error is set in the
        ``error`` property.  Otherwise, raise an error.
        """
        # set these before every call to clear them out
        self.returncode = None
        self.error = None

        prepend = kwargs['global_args'] if 'global_args' in kwargs else []

        args, unknown = self.parser.parse_known_args(
            prepend + [self.command_name] + list(argv))

        fail_on_error = kwargs.get('fail_on_error', True)

        # activate a workspace if one was specified on the command line

        if not args.no_workspace:
            ws = ramble.cmd.find_workspace(args)
            if ws:
                ramble.workspace.shell.activate(ws)
        else:
            ramble.workspace.shell.deactivate()

        out = StringIO()
        try:
            with log_output(out):
                self.returncode = _invoke_command(
                    self.command, self.parser, args, unknown)

        except SystemExit as e:
            self.returncode = e.code

        except BaseException as e:
            tty.debug(e)
            self.error = e
            if fail_on_error:
                self._log_command_output(out)
                raise

        if fail_on_error and self.returncode not in (None, 0):
            self._log_command_output(out)
            raise RambleCommandError(
                "Command exited with code %d: %s(%s)" % (
                    self.returncode, self.command_name,
                    ', '.join("'%s'" % a for a in argv)))

        return out.getvalue()

    def _log_command_output(self, out):
        if tty.is_verbose():
            fmt = self.command_name + ': {0}'
            for ln in out.getvalue().split('\n'):
                if len(ln) > 0:
                    tty.verbose(fmt.format(ln.replace('==> ', '')))


def _profile_wrapper(command, parser, args, unknown_args):
    import cProfile

    try:
        nlines = int(args.lines)
    except ValueError:
        if args.lines != 'all':
            tty.die('Invalid number for --lines: %s' % args.lines)
        nlines = -1

    # allow comma-separated list of fields
    sortby = ['time']
    if args.sorted_profile:
        sortby = args.sorted_profile.split(',')
        for stat in sortby:
            if stat not in stat_names:
                tty.die("Invalid sort field: %s" % stat)

    try:
        # make a profiler and run the code.
        pr = cProfile.Profile()
        pr.enable()
        return _invoke_command(command, parser, args, unknown_args)

    finally:
        pr.disable()

        # print out profile stats.
        stats = pstats.Stats(pr)
        stats.sort_stats(*sortby)
        stats.print_stats(nlines)


def print_setup_info(*info):
    """Print basic information needed by setup-env.[c]sh.

    Args:
        info (list): list of things to print: comma-separated list
            of 'csh', 'sh', or 'modules'

    This is in ``main.py`` to make it fast; the setup scripts need to
    invoke ramble in login scripts, and it needs to be quick.
    """
    shell = 'csh' if 'csh' in info else 'sh'

    def shell_set(var, value):
        if shell == 'sh':
            print("%s='%s'" % (var, value))
        elif shell == 'csh':
            print("set %s = '%s'" % (var, value))
        else:
            tty.die('shell must be sh or csh')


def _main(argv=None):
    """Logic for the main entry point for the Ramble command.

    ``main()`` calls ``_main()`` and catches any errors that emerge.

    ``_main()`` handles:

    1. Parsing arguments;
    2. Setting up configuration; and
    3. Finding and executing a Ramble command.

    Args:
        argv (list or None): command line arguments, NOT including
            the executable name. If None, parses from ``sys.argv``.

    """
    # ------------------------------------------------------------------------
    # main() is tricky to get right, so be careful where you put things.
    #
    # Things in this first part of `main()` should *not* require any
    # configuration. This doesn't include much -- setting up th parser,
    # restoring some key environment variables, very simple CLI options, etc.
    # ------------------------------------------------------------------------

    # Create a parser with a simple positional argument first.  We'll
    # lazily load the subcommand(s) we need later. This allows us to
    # avoid loading all the modules from ramble.cmd when we don't need
    # them, which reduces startup latency.
    parser = make_argument_parser()
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args, unknown = parser.parse_known_args(argv)

    # Recover stored LD_LIBRARY_PATH variables from ramble shell function
    # This is necessary because MacOS System Integrity Protection clears
    # (DY?)LD_LIBRARY_PATH variables on process start.
    # Ramble clears these variables before building and installing applications,
    # but needs to know the prior state for commands like
    # `ramble workspace activate that modify the user environment.
    recovered_vars = (
        'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH', 'DYLD_FALLBACK_LIBRARY_PATH'
    )
    for var in recovered_vars:
        stored_var_name = 'RAMBLE_%s' % var
        if stored_var_name in os.environ:
            os.environ[var] = os.environ[stored_var_name]

    # Just print help and exit if run with no arguments at all
    no_args = (len(sys.argv) == 1) if argv is None else (len(argv) == 0)
    if no_args:
        parser.print_help()
        return 1

    # -h, -H, and -V are special as they do not require a command, but
    # all the other options do nothing without a command.
    if args.version:
        print(get_version())
        return 0
    elif args.help:
        sys.stdout.write(parser.format_help(level=args.help))
        return 0

    # ------------------------------------------------------------------------
    # This part of the `main()` sets up Ramble's configuration.
    #
    # We set command line options (like --debug), then command line config
    # scopes, then workspace configuration here.
    # ------------------------------------------------------------------------

    # make ramble.config aware of any command line configuration scopes
    if args.config_scopes:
        ramble.config.command_line_scopes = args.config_scopes

    # ensure options on ramble command come before everything
    setup_main_options(args)

    # activate a workspace if one was specified on the command line
    workspace_format_error = None
    if not args.no_workspace:
        try:
            ws = ramble.cmd.find_workspace(args)
            if ws:
                ramble.workspace.shell.activate(ws)
        # print the context but delay this exception so that commands like
        # `ramble config edit` can still work with a bad workspace.
        except ramble.config.ConfigFormatError as e:
            e.print_context()
            workspace_format_error = e
        except jsonschema.exceptions.ValidationError as e:
            e.print_context()
            workspace_format_error = e
        except ruamel.yaml.parser.ParserError as e:
            workspace_format_error = e

    # ------------------------------------------------------------------------
    # Things that require configuration should go below here
    # ------------------------------------------------------------------------
    if args.print_shell_vars:
        print_setup_info(*args.print_shell_vars.split(','))
        return 0

    # At this point we've considered all the options to ramble itself, so we
    # need a command or we're done.
    if not args.command:
        parser.print_help()
        return 1

    # Try to load the particular command the caller asked for.
    cmd_name = args.command[0]
    cmd_name = aliases.get(cmd_name, cmd_name)

    # set up a bootstrap context, if asked.
    # bootstrap context needs to include parsing the command, b/c things
    # like `ConstraintAction` and `ConfigSetAction` happen at parse time.
    bootstrap_context = llnl.util.lang.nullcontext()

    # TODO (dwj): Do we need this?
    # if args.bootstrap:
    #   # import spack.bootstrap as bootstrap  # avoid circular imports
    #   # bootstrap_context = bootstrap.ensure_bootstrap_configuration()

    with bootstrap_context:
        return finish_parse_and_run(parser, cmd_name, workspace_format_error)


def finish_parse_and_run(parser, cmd_name, workspace_format_error):
    """Finish parsing after we know the command to run."""
    # add the found command to the parser and re-run then re-parse
    command = parser.add_command(cmd_name)
    args, unknown = parser.parse_known_args()

    # Now that we know what command this is and what its args are, determine
    # whether we can continue with a bad workspace and raise if not.
    edit_cmds = ["workspace", "config"]
    allowed_subcommands = ['edit', 'list']
    if workspace_format_error:
        raise_error = False
        if cmd_name.strip() in edit_cmds:
            tty.msg("Error while reading workspace config. In some cases this can be " +
                    "avoided by passing `-W` to ramble")
            raise_error = True
            subcommand = getattr(args, "%s_command" % cmd_name, None)
            if subcommand in allowed_subcommands:
                raise_error = False

        if raise_error:
            raise workspace_format_error

    # many operations will fail without a working directory.
    set_working_dir()

    # now we can actually execute the command.
    if args.ramble_profile or args.sorted_profile:
        _profile_wrapper(command, parser, args, unknown)
    elif args.pdb:
        import pdb
        pdb.runctx('_invoke_command(command, parser, args, unknown)',
                   globals(), locals())
        return 0
    else:
        return _invoke_command(command, parser, args, unknown)


def main(argv=None):
    """This is the entry point for the Ramble command.

    ``main()`` itself is just an error handler -- it handles errors for
    everything in Ramble that makes it to the top level.

    The logic is all in ``_main()``.

    Args:
        argv (list or None): command line arguments, NOT including
            the executable name. If None, parses from sys.argv.

    """
    try:
        return _main(argv)

    except RambleError as e:
        tty.debug(e)
        e.die()  # gracefully die on any RambleErrors

    except KeyboardInterrupt:
        if ramble.config.get('config:debug'):
            raise
        sys.stderr.write('\n')
        tty.error("Keyboard interrupt.")
        if sys.version_info >= (3, 5):
            return signal.SIGINT.value
        else:
            return signal.SIGINT

    except SystemExit as e:
        if ramble.config.get('config:debug'):
            traceback.print_exc()
        return e.code

    except Exception as e:
        if ramble.config.get('config:debug'):
            raise
        tty.error(e)
        return 3


class RambleCommandError(Exception):
    """Raised when RambleCommand execution fails."""
