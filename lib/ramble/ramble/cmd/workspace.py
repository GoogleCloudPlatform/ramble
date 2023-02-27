# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import sys
import tempfile

import llnl.util.tty as tty
import llnl.util.tty.color as color
from llnl.util.tty.colify import colify

import spack.util.string as string
from spack.util.editor import editor
import spack.util.environment

import ramble.cmd
import ramble.cmd.common.arguments
import ramble.cmd.common.arguments as arguments

import ramble.workspace
import ramble.workspace.shell
import ramble.expander

if sys.version_info >= (3, 3):
    from collections.abc import Sequence  # novm noqa: F401
else:
    from collections import Sequence  # noqa: F401


description = 'manage experiment workspaces'
section = 'workspaces'
level = 'short'

subcommands = [
    'activate',
    'archive',
    'deactivate',
    'create',
    'concretize',
    'setup',
    'analyze',
    'info',
    'edit',
    'mirror',
    ['list', 'ls'],
    ['remove', 'rm'],
]


def workspace_activate_setup_parser(subparser):
    """Set the current workspace"""
    shells = subparser.add_mutually_exclusive_group()
    shells.add_argument(
        '--sh', action='store_const', dest='shell', const='sh',
        help="print sh commands to activate the workspace")
    shells.add_argument(
        '--csh', action='store_const', dest='shell', const='csh',
        help="print csh commands to activate the workspace")
    shells.add_argument(
        '--fish', action='store_const', dest='shell', const='fish',
        help="print fish commands to activate the workspace")
    shells.add_argument(
        '--bat', action='store_const', dest='shell', const='bat',
        help="print bat commands to activate the environment")

    subparser.add_argument(
        '-p', '--prompt', action='store_true', default=False,
        help="decorate the command line prompt when activating")

    ws_options = subparser.add_mutually_exclusive_group()
    ws_options.add_argument(
        '--temp', action='store_true', default=False,
        help='create and activate a workspace in a temporary directory')
    ws_options.add_argument(
        '-d', '--dir', default=None,
        help="activate the workspace in this directory")
    ws_options.add_argument(
        metavar='workspace', dest='activate_workspace', nargs='?', default=None,
        help='name of workspace to activate')


def create_temp_workspace_directory():
    """
    Returns the path of a temporary directory in which to
    create a workspace
    """
    return tempfile.mkdtemp(prefix="ramble-")


def workspace_activate(args):
    if not args.activate_workspace and not args.dir and not args.temp:
        tty.die('ramble workspace activate requires a workspace name, directory, or --temp')

    if not args.shell:
        ramble.cmd.common.shell_init_instructions(
            "ramble workspace activate",
            "    eval `ramble workspace activate {sh_arg} [...]`")
        return 1

    workspace_name_or_dir = args.activate_workspace or args.dir

    # Temporary workspace
    if args.temp:
        workspace = create_temp_workspace_directory()
        workspace_path = os.path.abspath(workspace)
        short_name = os.path.basename(workspace_path)
        ramble.workspace.Workspace(workspace).write()

    # Named workspace
    elif ramble.workspace.exists(workspace_name_or_dir) and not args.dir:
        workspace_path = ramble.workspace.root(workspace_name_or_dir)
        short_name = workspace_name_or_dir

    # Workspace directory
    elif ramble.workspace.is_workspace_dir(workspace_name_or_dir):
        workspace_path = os.path.abspath(workspace_name_or_dir)
        short_name = os.path.basename(workspace_path)

    else:
        tty.die("No such workspace: '%s'" % workspace_name_or_dir)

    workspace_prompt = '[%s]' % short_name

    # We only support one active workspace at a time, so deactivate the current one.
    if ramble.workspace.active_workspace() is None:
        cmds = ''
        env_mods = spack.util.environment.EnvironmentModifications()
    else:
        cmds = ramble.workspace.shell.deactivate_header(shell=args.shell)
        env_mods = ramble.workspace.shell.deactivate()

    # Activate new workspace
    active_workspace = ramble.workspace.Workspace(workspace_path)
    cmds += ramble.workspace.shell.activate_header(
        ws=active_workspace,
        shell=args.shell,
        prompt=workspace_prompt if args.prompt else None
    )
    env_mods.extend(ramble.workspace.shell.activate(
        ws=active_workspace
    ))
    cmds += env_mods.shell_modifications(args.shell)
    sys.stdout.write(cmds)


def workspace_deactivate_setup_parser(subparser):
    """deactivate any active workspace in the shell"""
    shells = subparser.add_mutually_exclusive_group()
    shells.add_argument(
        '--sh', action='store_const', dest='shell', const='sh',
        help="print sh commands to deactivate the workspace")
    shells.add_argument(
        '--csh', action='store_const', dest='shell', const='csh',
        help="print csh commands to deactivate the workspace")
    shells.add_argument(
        '--fish', action='store_const', dest='shell', const='fish',
        help="print fish commands to activate the workspace")
    shells.add_argument(
        '--bat', action='store_const', dest='shell', const='bat',
        help="print bat commands to activate the environment")


def workspace_deactivate(args):
    if not args.shell:
        ramble.cmd.common.shell_init_instructions(
            "ramble workspace deactivate",
            "    eval `ramble workspace deactivate {sh_arg}`",
        )
        return 1

    # Error out when -w, -W, -D flags are given, cause they are ambiguous.
    if args.workspace or args.no_workspace or args.workspace_dir:
        tty.die('Calling ramble workspace deactivate with --workspace,'
                ' --workspace-dir, and --no-workspace '
                'is ambiguous')

    if ramble.workspace.active_workspace() is None:
        tty.die('No workspace is currently active.')

    cmds = ramble.workspace.shell.deactivate_header(args.shell)
    env_mods = ramble.workspace.shell.deactivate()
    cmds += env_mods.shell_modifications(args.shell)
    sys.stdout.write(cmds)


def workspace_create_setup_parser(subparser):
    """create a new workspace"""
    subparser.add_argument(
        'create_workspace', metavar='wrkspc',
        help='name of workspace to create')
    subparser.add_argument(
        '-c', '--config',
        help='configuration file to create workspace with')
    subparser.add_argument(
        '-t', '--template_execute',
        help='execution template file to use when creating workspace')
    subparser.add_argument(
        '-d', '--dir', action='store_true',
        help='create a workspace in a specific directory')


def workspace_create(args):
    _workspace_create(args.create_workspace, args.dir,
                      args.config, args.template_execute)


def _workspace_create(name_or_path, dir=False,
                      config=None, template_execute=None):
    """Create a new workspace

    Arguments:
        name_or_path (str): name of the workspace to create, or path
                            to it
        dir (bool): if True, create a workspace in a directory instead
            of a named workspace
        config (str): path to a configuration file that should
                      generate the workspace
        template_execute (str): Path to a template execute script to
                                create the workspace with
    """

    if dir:
        workspace = ramble.workspace.Workspace(name_or_path)
        workspace.write()
        tty.msg("Created workspace in %s" % workspace.path)
        tty.msg("You can activate this workspace with:")
        tty.msg("  ramble workspace activate %s" % workspace.path)
    else:
        workspace = ramble.workspace.create(name_or_path)
        workspace.write()
        tty.msg("Created workspace in %s" % name_or_path)
        tty.msg("You can activate this workspace with:")
        tty.msg("  ramble workspace activate %s" % name_or_path)

    if config:
        with open(config, 'r') as f:
            workspace._read_config('workspace', f)
            workspace._write_config('workspace')

    if template_execute:
        with open(template_execute, 'r') as f:
            _, file_name = os.path.split(template_execute)
            template_name = os.path.splitext(file_name)[0]
            workspace._read_template(template_name, f.read())
            workspace._write_templates()

    return workspace


def workspace_remove_setup_parser(subparser):
    """remove an existing workspace"""
    subparser.add_argument(
        'rm_wrkspc', metavar='wrkspc', nargs='+',
        help='workspace(s) to remove')
    arguments.add_common_arguments(subparser, ['yes_to_all'])


def workspace_remove(args):
    """Remove a *named* workspace.

    This removes an environment managed by Ramble. Directory workspaces
    should be removed manually.
    """
    read_workspaces = []
    for workspace_name in args.rm_wrkspc:
        workspace = ramble.workspace.read(workspace_name)
        read_workspaces.append(workspace)

    tty.debug('Removal args: {}'.format(args))

    if not args.yes_to_all:
        answer = tty.get_yes_or_no(
            'Really remove %s %s?' % (
                string.plural(len(args.rm_wrkspc), 'workspace', show_n=False),
                string.comma_and(args.rm_wrkspc)),
            default=False)
        if not answer:
            tty.die("Will not remove any workspaces")

    for workspace in read_workspaces:
        if workspace.active:
            tty.die("Workspace %s can't be removed while activated."
                    % workspace.name)

        workspace.destroy()
        tty.msg("Successfully removed workspace '%s'" % workspace.name)


def workspace_concretize_setup_parser(subparser):
    """Concretize a workspace"""
    pass


def workspace_concretize(args):
    ws = ramble.cmd.require_active_workspace(cmd_name='workspace concretize')

    tty.debug('Concretizing workspace')
    ws.concretize()


def workspace_setup_setup_parser(subparser):
    """Setup a workspace"""
    subparser.add_argument(
        '--dry-run', dest='dry_run',
        action='store_true',
        help='perform a dry run. Sets up directories and generates ' +
             'all scripts. Prints commands that would be executed ' +
             'for installation, and files that would be downloaded.')


def workspace_setup(args):
    ws = ramble.cmd.require_active_workspace(cmd_name='workspace setup')

    if args.dry_run:
        ws.dry_run = True

    tty.debug('Setting up workspace')
    with ws.write_transaction():
        ws.run_pipeline('setup')


def workspace_analyze_setup_parser(subparser):
    """Analyze a workspace"""
    subparser.add_argument(
        '-f', '--formats', dest='output_formats',
        nargs='+',
        default=['text'],
        help='list of output formats to write.' +
             'Supported formats are json, yaml, or text',
        required=False)


def workspace_analyze(args):
    ws = ramble.cmd.require_active_workspace(cmd_name='workspace analyze')

    tty.debug('Analyzing workspace')
    with ws.write_transaction():
        ws.run_pipeline('analyze')
        ws.dump_results(output_formats=args.output_formats)


header_color = '@*b'
level1_color = '@*g'
level2_color = '@*r'
level3_color = '@*c'
level4_color = '@*m'
plain_format = '@.'


def section_title(s):
    return header_color + s + plain_format


def nested_1(s):
    return level1_color + s + plain_format


def nested_2(s):
    return level2_color + s + plain_format


def nested_3(s):
    return level3_color + s + plain_format


def nested_4(s):
    return level4_color + s + plain_format


def workspace_info_setup_parser(subparser):
    """Information about a workspace"""
    pass


def workspace_info(args):
    ws = ramble.cmd.require_active_workspace(cmd_name='workspace info')

    color.cprint(section_title('Workspace: ') + ws.name)
    color.cprint('')
    color.cprint(section_title('Location: ') + ws.path)
    color.cprint('')

    # Print workspace templates that currently exist
    color.cprint(section_title('Workspace Templates:'))
    for template, _ in ws.all_templates():
        color.cprint('    %s' % template)

    # Print workspace variables information
    workspace_vars = ws.get_workspace_vars()
    if workspace_vars:
        color.cprint('')
        color.cprint(section_title('Workspace Variables:'))
        for arg, val in workspace_vars.items():
            color.cprint('  - %s = %s' % (arg, val))

    # Print experiment information
    expander = ramble.expander.Expander(ws)
    color.cprint('')
    color.cprint(section_title('Experiments:'))
    for app, workloads, app_vars, app_env_vars in ws.all_applications():
        color.cprint(nested_1('  Application: ') + app)
        expander.set_application(app)
        expander.set_application_vars(app_vars)
        if app_vars:
            color.cprint(nested_4('    Application Parameters:'))
            for name, value in app_vars.items():
                color.cprint('      %s = %s --> %s'
                             % (name, value, expander.expand_var(value)))

        for workload, experiments, workload_vars, workload_env_vars in \
                ws.all_workloads(workloads):
            color.cprint(nested_2('    Workload: ') + workload)
            expander.set_workload(workload)
            expander.set_workload_vars(workload_vars)
            if workload_vars:
                color.cprint(nested_4('      Workload Parameters:'))
                for name, value in workload_vars.items():
                    color.cprint('        %s = %s --> %s'
                                 % (name, value, expander.expand_var(value)))

            for exp, _, exp_vars, exp_env_vars, exp_matrices in ws.all_experiments(experiments):
                expander.set_experiment(exp)
                expander.set_experiment_vars(exp_vars)
                expander.set_experiment_matrices(exp_matrices)

                for _ in expander.rendered_experiments():
                    color.cprint(nested_3('      Experiment: ') +
                                 expander.experiment_name)

                    color.cprint(nested_4('        Experiment Parameters:'))
                    rendered_vars = expander.get_level_vars(level='experiment')
                    if 'experiment_name' in rendered_vars:
                        del rendered_vars['experiment_name']

                    for name, value in rendered_vars.items():
                        color.cprint('          %s = %s --> %s'
                                     % (name, value, expander.expand_var(value)))

    # Print MPI command
    color.cprint('')
    color.cprint(section_title('MPI Command:'))
    color.cprint('    %s' % ws.mpi_command)

    # Print software stack information
    color.cprint('')
    color.cprint(section_title('Software Stack:'))
    comp_str = 'compilers'
    mpi_str = 'mpi_libraries'
    app_str = 'applications'

    spack_dict = ws.get_spack_dict()
    if comp_str in spack_dict:
        color.cprint(nested_1('  Compilers:'))
        for name, info in spack_dict[comp_str].items():
            spec = ws._build_spec_dict(info)
            spec_str = ws.spec_string(spec).replace('@', '@@')
            color.cprint('    %s = %s' % (name, spec_str))
    if mpi_str in spack_dict:
        color.cprint(nested_1('  MPI Libraries:'))
        for name, info in spack_dict[mpi_str].items():
            spec = ws._build_spec_dict(info)
            spec_str = ws.spec_string(spec).replace('@', '@@')
            color.cprint('    %s = %s' % (name, spec_str))
    if app_str in spack_dict:
        color.cprint(nested_1('  Application Specs:'))
        for app, specs in spack_dict[app_str].items():
            color.cprint(nested_2('    %s:' % app))
            for name, info in specs.items():
                spec = ws._build_spec_dict(info, app)
                spec['application_name'] = app
                spec_str = ws.spec_string(spec).replace('@', '@@')
                color.cprint('      %s = %s' % (name, spec_str))
                ws_name = ' ' * (len(name) + 2)
                if 'compiler' in info:
                    color.cprint('      %s compiler = %s' %
                                 (ws_name, info['compiler']))
                if 'mpi' in info:
                    color.cprint('      %s mpi = %s' %
                                 (ws_name, info['mpi']))


#
# workspace list
#


def workspace_list_setup_parser(subparser):
    """list available workspaces"""
    pass


def workspace_list(args):
    names = ramble.workspace.all_workspace_names()

    color_names = []
    for name in names:
        if ramble.workspace.active(name):
            name = color.colorize('@*g{%s}' % name)
        color_names.append(name)

    # say how many there are if writing to a tty
    if sys.stdout.isatty():
        if not names:
            tty.msg('No workspaces')
        else:
            tty.msg('%d workspaces' % len(names))

    colify(color_names, indent=4)


def workspace_edit_setup_parser(subparser):
    """edit workspace config or template"""
    subparser.add_argument(
        '-t', '--template', dest='edit_template',
        default='',
        help='template name to edit. If not set, defaults to editing ramble.yaml. '
             + 'Errors if template does not exist and `--create` is not used',
        required=False)
    subparser.add_argument(
        '--print-file', action='store_true',
        help='print the file name that would be edited')
    subparser.add_argument(
        '--create', '-c', action='store_true',
        help='create template if it does not exist.')


def workspace_edit(args):
    ramble_ws = ramble.cmd.find_workspace_path(args)

    if not ramble_ws:
        tty.die('ramble workspace edit requires either a command '
                'line workspace or an active workspace')

    if not args.edit_template:
        edit_file = ramble.workspace.config_file(ramble_ws)
    else:
        edit_file = ramble.workspace.template_path(ramble_ws,
                                                   args.edit_template)

        if args.create and not os.path.exists(edit_file):
            f = open(edit_file, 'w+')
            f.close()

        if not os.path.exists(edit_file):
            tty.die('File for template %s does not exist.' % (args.edit_template))

    if args.print_file:
        print(edit_file)
    else:
        editor(edit_file)


def workspace_archive_setup_parser(subparser):
    """archive current workspace state"""
    subparser.add_argument(
        '--tar-archive', '-t', action='store_true',
        dest='tar_archive',
        help='create a tar.gz of the archive directory for backing up.')

    subparser.add_argument(
        '--upload-url', '-u', dest='upload_url',
        default=None,
        help='URL to upload tar archive into. Does nothing if `-t` is not specified.')


def workspace_archive(args):
    ws = ramble.cmd.require_active_workspace(cmd_name='workspace archive')

    ws.archive(create_tar=args.tar_archive,
               archive_url=args.upload_url)


def workspace_mirror_setup_parser(subparser):
    """mirror current workspace state"""
    subparser.add_argument(
        '-d', dest='mirror_path',
        default=None,
        help='Path to create mirror in.')

    subparser.add_argument(
        '--dry-run', dest='dry_run',
        action='store_true',
        help='perform a dry run. Creates spack environments, ' +
             'prints commands that would be executed ' +
             'for installation, and files that would be downloaded.')


def workspace_mirror(args):
    ws = ramble.cmd.require_active_workspace(cmd_name='workspace archive')

    if args.dry_run:
        ws.dry_run = True

    ws.create_mirror(args.mirror_path)
    ws.run_pipeline('mirror')


#: Dictionary mapping subcommand names and aliases to functions
subcommand_functions = {}


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar='SUBCOMMAND',
                                  dest='workspace_command')

    for name in subcommands:
        if isinstance(name, (list, tuple)):
            name, aliases = name[0], name[1:]
        else:
            aliases = []

        # add commands to subcommands dict
        function_name = 'workspace_%s' % name
        function = globals()[function_name]
        for alias in [name] + aliases:
            subcommand_functions[alias] = function

        # make a subparser and run the command's setup function on it
        setup_parser_cmd_name = 'workspace_%s_setup_parser' % name
        setup_parser_cmd = globals()[setup_parser_cmd_name]

        subsubparser = sp.add_parser(
            name, aliases=aliases, help=setup_parser_cmd.__doc__)
        setup_parser_cmd(subsubparser)


def workspace(parser, args):
    """Look for a function called environment_<name> and call it."""
    action = subcommand_functions[args.workspace_command]
    action(args)
