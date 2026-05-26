# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy

import ramble.config
import ramble.workspace
from ramble.util.logger import logger

description = "manage global or workspace-scoped filter groups"
section = "config"
level = "long"


def setup_parser(subparser):
    scopes = ramble.config.scopes()
    # Add 'workspace' as a scope option for this command
    scopes = list(scopes) + ["workspace"]

    subparser.add_argument(
        "--scope",
        choices=scopes,
        default="user",  # Default to global (user) scope
        help="configuration scope to modify (default: %(default)s)",
    )

    actions = subparser.add_subparsers(metavar="ACTION", dest="action")

    add_parser = actions.add_parser("add", help="add a filter group")
    add_parser.add_argument("-n", "--name", required=True, help="name of filter group")
    add_parser.add_argument(
        "-w",
        "--where",
        action="append",
        help="inclusive filter expression. Can be specified multiple times.",
    )
    add_parser.add_argument(
        "-ew",
        "--exclude-where",
        dest="exclude_where",
        action="append",
        help="exclusive filter expression. Can be specified multiple times.",
    )

    remove_parser = actions.add_parser("remove", aliases=["rm"], help="remove a filter group")
    remove_parser.add_argument("-n", "--name", required=True, help="name of filter group")

    actions.add_parser("list", help="list defined filter groups")
    actions.add_parser("blame", help="show defined filter groups with sources")


def _resolve_scope(args):
    scope = args.scope
    if scope == "workspace":
        ws = ramble.workspace.active_workspace()
        if not ws:
            logger.die("Workspace scope requires an active workspace")
        scope = ws.ws_file_config_scope_name()
    return scope


def filter_groups(parser, args):
    action = args.action
    if not action:
        parser.print_help()
        return

    scope = _resolve_scope(args)

    if action == "add":
        filter_groups_add(scope, args)
    elif action in ("remove", "rm"):
        filter_groups_remove(scope, args)
    elif action == "list":
        filter_groups_list(scope, args)
    elif action == "blame":
        filter_groups_blame(args)


def filter_groups_add(scope, args):
    name = args.name

    if not args.where and not args.exclude_where:
        logger.die("At least one of --where or --exclude-where must be specified.")

    group_def = {}
    if args.where:
        group_def["where"] = args.where
    if args.exclude_where:
        group_def["exclude_where"] = args.exclude_where

    existing = ramble.config.get(f"filter_groups:{name}", scope=scope)
    if existing:
        logger.msg(f"Updating existing filter group '{name}' in scope '{scope}'.")
    else:
        logger.msg(f"Adding filter group '{name}' to scope '{scope}'.")

    ws = ramble.workspace.active_workspace()
    if ws and scope == ws.ws_file_config_scope_name():
        with ws.write_transaction():
            ramble.config.set(f"filter_groups:{name}", group_def, scope=scope)
    else:
        ramble.config.set(f"filter_groups:{name}", group_def, scope=scope)


def filter_groups_remove(scope, args):
    name = args.name

    existing = ramble.config.get(f"filter_groups:{name}", scope=scope)
    if not existing:
        logger.die(f"Filter group '{name}' not found in scope '{scope}'.")

    logger.msg(f"Removing filter group '{name}' from scope '{scope}'.")

    groups = ramble.config.get("filter_groups", scope=scope)
    if groups:
        groups = copy.deepcopy(groups)
        groups.pop(name, None)

        ws = ramble.workspace.active_workspace()
        if ws and scope == ws.ws_file_config_scope_name():
            with ws.write_transaction():
                ramble.config.set("filter_groups", groups, scope=scope)
        else:
            ramble.config.set("filter_groups", groups, scope=scope)


def filter_groups_list(scope, args):
    groups = ramble.config.get("filter_groups", scope=scope)
    if not groups:
        logger.msg(f"No filter groups defined in scope '{scope}'.")
        return

    logger.msg(f"Filter groups defined in scope '{scope}':")
    for name, definition in groups.items():
        logger.msg(f"  {name}:")
        if "where" in definition:
            logger.msg("    where:")
            for w in definition["where"]:
                logger.msg(f"      - {w}")
        if "exclude_where" in definition:
            logger.msg("    exclude_where:")
            for ew in definition["exclude_where"]:
                logger.msg(f"      - {ew}")


def filter_groups_blame(args):
    logger.msg("Active filter groups (with sources):")
    for scope in ramble.config.config:
        try:
            groups = ramble.config.config.get_config("filter_groups", scope=scope.name)
            if groups:
                try:
                    filename = scope.get_section_filename("filter_groups")
                except NotImplementedError:
                    filename = "internal"
                logger.msg(f"Scope: {scope.name} ({filename})")
                for name, definition in groups.items():
                    logger.msg(f"  {name}:")
                    if "where" in definition:
                        logger.msg("    where:")
                        for w in definition["where"]:
                            logger.msg(f"      - {w}")
                    if "exclude_where" in definition:
                        logger.msg("    exclude_where:")
                        for ew in definition["exclude_where"]:
                            logger.msg(f"      - {ew}")
        except Exception:
            pass
