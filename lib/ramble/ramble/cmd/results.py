# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import llnl.util.tty as tty

from ramble.config import ConfigError
import ramble.experimental.uploader


description = "take actions on experiment results"
section = "workspaces"
level = "short"

subcommands = [
    'file_upload',
]

#: Dictionary mapping subcommand names and aliases to functions
subcommand_functions = {}


def results_file_upload_setup_parser(subparser):
    subparser.add_argument(
        'filename', metavar='filename',
        help='path of file to upload')


def results_file_upload(args):
    """Imports Ramble experiment results from JSON file and uploads them."""
    imported_results = ramble.experimental.uploader.results_file_import(args.filename)

    if ramble.config.get('config:upload'):
        # Read upload type and push it there
        if ramble.config.get('config:upload:type') == 'BigQuery':  # TODO: enum?
            try:
                formatted_data = ramble.experimental.uploader.format_data(imported_results)
            except KeyError:
                tty.die("Error parsing file: Does not contain valid data.")

            # TODO: strategy object?
            uploader = ramble.experimental.uploader.BigQueryUploader()

            # Read workspace name from results for uploader, or use default.
            try:
                workspace_name = formatted_data[0].workspace_name
            except KeyError:
                workspace_name = "Default Workspace"

            uri = ramble.config.get('config:upload:uri')
            if not uri:
                tty.die('No upload URI (config:upload:uri) in config.')

            tty.msg('Uploading Results to ' + uri)
            uploader.perform_upload(uri, workspace_name, formatted_data)
        else:
            raise ConfigError("Unknown config:upload:type value")

    else:
        raise ConfigError("Missing correct conifg:upload parameters")


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar='SUBCOMMAND',
                                  dest='results_command')

    for name in subcommands:
        if isinstance(name, (list, tuple)):
            name, aliases = name[0], name[1:]
        else:
            aliases = []

        # add commands to subcommands dict
        function_name = 'results_%s' % name
        function = globals()[function_name]
        for alias in [name] + aliases:
            subcommand_functions[alias] = function

        # make a subparser and run the command's setup function on it
        setup_parser_cmd_name = 'results_%s_setup_parser' % name
        setup_parser_cmd = globals()[setup_parser_cmd_name]

        subsubparser = sp.add_parser(
            name, aliases=aliases, help=setup_parser_cmd.__doc__)
        setup_parser_cmd(subsubparser)


def results(parser, args):
    """Look for a function called environment_<name> and call it."""
    action = subcommand_functions[args.results_command]
    action(args)
