# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

description = "manage data and databases"
section = "data"
level = "short"

subcommands = [
    "create-db",
]


def data_create_db_setup_parser(subparser):
    """create the database"""
    pass


def data_create_db(args):
    """create the database"""
    import ramble.config
    import ramble.uploader
    from ramble.config import ConfigError

    uri = ramble.config.get("config:upload:uri")
    if not uri:
        raise ConfigError("No upload URI (config:upload:uri) in config.")

    uploader_type_str = ramble.config.get("config:upload:type")

    if uploader_type_str is None:
        raise ConfigError("No upload type (config:upload:type) in config.")

    if not hasattr(ramble.uploader.uploader_types, uploader_type_str):
        raise ConfigError(f"Upload type {uploader_type_str} is not valid.")

    uploader_type = getattr(ramble.uploader.uploader_types, uploader_type_str)

    if uploader_type == ramble.uploader.uploader_types.BigQuery:
        uploader = ramble.uploader.BigQueryUploader()
    elif uploader_type == ramble.uploader.uploader_types.SQLite:
        uploader = ramble.uploader.SQLiteUploader()
    else:
        # Note: PrintOnlyUploader shouldn't really be used here since it doesn't create tables
        uploader = ramble.uploader.PrintOnlyUploader()

    if hasattr(uploader, "create_tables"):
        uploader.create_tables(uri)
    else:
        # Some uploaders might not have/need create_tables (like PrintOnly)
        pass


#: Dictionary mapping subcommand names and aliases to functions
subcommand_functions = {}


def sanitize_arg_name(base_name):
    """Allow function names to be remapped (eg `-` to `_`)"""
    formatted_name = base_name.replace("-", "_")
    return formatted_name


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest="data_command")

    for name in subcommands:
        if isinstance(name, (list, tuple)):
            name, aliases = name[0], name[1:]
        else:
            aliases = []

        # add commands to subcommands dict
        function_name = sanitize_arg_name(f"data_{name}")

        function = globals()[function_name]
        for alias in [name] + aliases:
            subcommand_functions[alias] = function

        # make a subparser and run the command's setup function on it
        setup_parser_cmd_name = sanitize_arg_name(f"data_{name}_setup_parser")
        setup_parser_cmd = globals()[setup_parser_cmd_name]

        subsubparser = sp.add_parser(
            name,
            aliases=aliases,
            help=setup_parser_cmd.__doc__,
            description=setup_parser_cmd.__doc__,
        )
        setup_parser_cmd(subsubparser)


def data(parser, args, unknown_args=None):
    """Look for a function called data_<name> and call it."""
    action = subcommand_functions[args.data_command]
    action(args)
