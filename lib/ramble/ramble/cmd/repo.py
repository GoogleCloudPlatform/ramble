# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import os
import sys

import ramble.cmd.common.arguments
import ramble.config
import ramble.repository
from ramble.util.logger import logger

description = "manage Ramble repositories"
section = "config"
level = "long"


def setup_parser(subparser):
    """Setup the repo command parser.

    The repo command helps manage Ramble repositories, which are
    the locations ramble reads object definition files from.

    This command has subcommands for create, add, remove, and list.
    """

    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest="repo_command")
    scopes = ramble.config.scopes()
    scopes_metavar = ramble.config.scopes_metavar

    # Create
    create_parser = sp.add_parser(
        "create", help=repo_create.__doc__, description=repo_create.__doc__
    )
    create_parser.add_argument("directory", help="directory to create the repo in")
    create_parser.add_argument(
        "namespace",
        metavar="new_namespace",
        help="namespace to identify objects " "in the repository. defaults to the directory name",
        nargs="?",
    )
    create_parser.add_argument(
        "-d",
        "--subdirectory",
        action="store",
        help=(
            "subdirectory to store objects in the repository. "
            "Default is determined by the type of repository. "
            "Use an empty string for no subdirectory."
        ),
    )
    ramble.cmd.common.arguments.add_common_arguments(create_parser, ["repo_type"])

    # List
    list_parser = sp.add_parser("list", help=repo_list.__doc__, description=repo_list.__doc__)
    list_parser.add_argument(
        "--scope",
        choices=scopes,
        metavar=scopes_metavar,
        default=ramble.config.default_list_scope(),
        help="configuration scope to read from",
    )
    ramble.cmd.common.arguments.add_common_arguments(list_parser, ["repo_type"])

    # Add
    add_parser = sp.add_parser("add", help=repo_add.__doc__, description=repo_add.__doc__)
    add_parser.add_argument("path", help="path to a Ramble repository directory")
    add_parser.add_argument(
        "--scope",
        choices=scopes,
        metavar=scopes_metavar,
        default=ramble.config.default_modify_scope(),
        help="configuration scope to modify",
    )
    ramble.cmd.common.arguments.add_common_arguments(add_parser, ["repo_type"])

    # Remove
    remove_parser = sp.add_parser(
        "remove", help=repo_remove.__doc__, description=repo_remove.__doc__, aliases=["rm"]
    )
    remove_parser.add_argument(
        "namespace_or_path", help="namespace or path of a Ramble repository"
    )
    remove_parser.add_argument(
        "--scope",
        choices=scopes,
        metavar=scopes_metavar,
        default=ramble.config.default_modify_scope(),
        help="configuration scope to modify",
    )
    ramble.cmd.common.arguments.add_common_arguments(remove_parser, ["repo_type"])


def repo_create(args):
    """Create a new repository."""
    if args.type == "any":
        unified_repo = True
        obj_type = ramble.repository.default_type
        repo_type = "applications and modifiers"
        register_type = ""
    else:
        unified_repo = False
        obj_type = ramble.repository.ObjectTypes[args.type]
        repo_type = ramble.repository.ObjectTypes[args.type].name
        register_type = f" -t {repo_type}"

    subdir = args.subdirectory

    full_path, namespace = ramble.repository.create_repo(
        args.directory, args.namespace, subdir, object_type=obj_type, unified_repo=unified_repo
    )
    logger.msg(f"Created {repo_type} repo with namespace '{namespace}'.")
    logger.msg(
        "To register it with ramble, run this command:",
        f"ramble repo{register_type} add {full_path}",
    )


def repo_add(args):
    """Add a repository to Ramble's configuration."""
    path = args.path
    # real_path is absolute and handles substitution.
    canon_path = ramble.util.path.canonicalize_path(path)
    # check if the path exists
    if not os.path.exists(canon_path):
        logger.die(f"No such file or directory: {path}")

    # Make sure the path is a directory.
    if not os.path.isdir(canon_path):
        logger.die(f"Not a Ramble repository: {path}")

    if args.type == "any":
        obj_types = ramble.repository.ObjectTypes
        # When types are not explicitly specified, allow
        # some (but not all) object types to be missing
        # from the given repo.
        first_repo = None
        for obj_type in obj_types:
            try:
                first_repo = ramble.repository.Repo(canon_path, obj_type)
                break
            except ramble.repository.BadRepoError:
                continue

        if not first_repo:
            raise ramble.repository.BadRepoError(
                f"The given path {path} is not a valid repo for any object types"
            )

        # Now that we know it is a valid repo for at least one object type,
        # add it for all of them.
        for obj_type in obj_types:
            type_def = ramble.repository.type_definitions[obj_type]
            repos = ramble.config.get(type_def["config_section"], scope=args.scope) or []
            if canon_path in [ramble.util.path.canonicalize_path(r) for r in repos]:
                logger.warn(
                    f"{obj_type.name} repository is already registered with Ramble: {path}"
                )
            else:
                repos.insert(0, canon_path)
                ramble.config.set(type_def["config_section"], repos, args.scope)
                logger.msg(f"Added {obj_type.name} repo with namespace '{first_repo.namespace}'.")
    else:
        obj_types = [ramble.repository.ObjectTypes[args.type]]
        allow_partial = False
        added = False
        for obj_type in obj_types:
            type_def = ramble.repository.type_definitions[obj_type]

            # Make sure it's actually a ramble repository by constructing it.
            try:
                repo = ramble.repository.Repo(canon_path, obj_type)
            except ramble.repository.BadRepoError as e:
                if not allow_partial:
                    # Wrap the error to give a clearer message
                    raise ramble.repository.BadRepoError(
                        f"Failed to find valid repo with type {obj_type}"
                    ) from e
                repo = None

            # If that succeeds, finally add it to the configuration.
            if not repo:
                continue
            repos = ramble.config.get(type_def["config_section"], scope=args.scope)
            if not repos:
                repos = []

            if repo.root in repos or path in repos:
                logger.warn(
                    f"{obj_type.name} repository is already registered with Ramble: {path}"
                )
            else:
                repos.insert(0, canon_path)
                ramble.config.set(type_def["config_section"], repos, args.scope)
                logger.msg(f"Added {obj_type.name} repo with namespace '{repo.namespace}'.")
            added = True
        if not added:
            raise ramble.repository.BadRepoError(
                f"The given path {path} is not a valid repo for any object types"
            )


def repo_remove(args):
    """Remove a repository from Ramble's configuration."""
    if args.type == "any":
        obj_types = ramble.repository.ObjectTypes
    else:
        obj_types = [ramble.repository.ObjectTypes[args.type]]

    if args.scope:
        scopes_to_check = [args.scope]
    else:
        # Highest precedence first
        scopes_to_check = reversed([s.name for s in ramble.config.config.file_scopes])

    repo_removed = False
    for scope in scopes_to_check:
        for obj_type in obj_types:
            type_def = ramble.repository.type_definitions[obj_type]
            repos = ramble.config.get(type_def["config_section"], scope=scope)
            if not repos:
                continue

            namespace_or_path = args.namespace_or_path

            canon_path = ramble.util.path.canonicalize_path(namespace_or_path)
            normalized_path_to_remove = os.path.normcase(os.path.normpath(canon_path))

            path_found_and_removed = False
            for repo_path in repos:
                repo_canon_path = ramble.util.path.canonicalize_path(repo_path)
                normalized_repo_path = os.path.normcase(os.path.normpath(repo_canon_path))
                if normalized_path_to_remove == normalized_repo_path:
                    repos.remove(repo_path)
                    ramble.config.set(type_def["config_section"], repos, scope)
                    logger.msg(
                        f"Removed {obj_type.name} repository {repo_path} from scope '{scope}'."
                    )
                    repo_removed = True
                    path_found_and_removed = True
                    break  # move to next obj_type

            if path_found_and_removed:
                continue

            for path in list(repos):
                try:
                    repo = ramble.repository.Repo(path, obj_type)
                    if repo.namespace == namespace_or_path:
                        repos.remove(path)
                        ramble.config.set(type_def["config_section"], repos, scope)
                        logger.msg(
                            f"Removed {obj_type.name} repository {repo.root} "
                            f"with namespace '{repo.namespace}' from scope '{scope}'."
                        )
                        repo_removed = True
                        break
                except ramble.repository.RepoError:
                    continue

        if repo_removed and not args.scope:
            break

    if not repo_removed:
        all_types = [str(obj_type.name) for obj_type in obj_types]
        logger.die(
            f"No repository for {all_types} with path or namespace: {args.namespace_or_path}"
        )


def repo_list(args):
    """Show registered repositories and their namespaces."""
    if args.type == "any":
        obj_types = ramble.repository.ObjectTypes
    else:
        obj_types = [ramble.repository.ObjectTypes[args.type]]

    for obj_type in obj_types:
        type_def = ramble.repository.type_definitions[obj_type]

        roots = ramble.config.get(type_def["config_section"], scope=args.scope)
        repos = []
        for r in roots:
            try:
                repos.append(ramble.repository.Repo(r, obj_type))
            except ramble.repository.RepoError:
                continue

        if sys.stdout.isatty():
            msg = f"{len(repos)} {obj_type.name} repositor"
            msg += "y." if len(repos) == 1 else "ies."
            logger.msg(msg)

        if not repos:
            return

        max_ns_len = max(len(r.namespace) for r in repos)
        for repo in repos:
            fmt = "%%-%ds%%s" % (max_ns_len + 4)
            print(fmt % (repo.namespace, repo.root))


def repo(parser, args):
    action = {
        "create": repo_create,
        "list": repo_list,
        "add": repo_add,
        "remove": repo_remove,
        "rm": repo_remove,
    }

    if args.type != "any" and args.type not in ramble.repository.OBJECT_NAMES:
        logger.die(f"Repository type '{args.type}' is not valid.")

    action[args.repo_command](args)
