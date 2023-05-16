# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from __future__ import print_function

import os
import sys

import llnl.util.tty as tty

import ramble.config
import ramble.repository

description = "manage application repositories"
section = "config"
level = "long"


def setup_parser(subparser):
    """Setup the repo command parser.

    The repo command helps manage application repositories, which are
    the locations ramble reads application definition files from.

    This command has subcommands for create, add, remove, and list.
    """
    sp = subparser.add_subparsers(metavar='SUBCOMMAND', dest='repo_command')
    scopes = ramble.config.scopes()
    scopes_metavar = ramble.config.scopes_metavar

    default_type_def = ramble.repository.type_definitions[ramble.repository.default_type]

    # Create
    create_parser = sp.add_parser('create', help=repo_create.__doc__)
    create_parser.add_argument(
        'directory', help="directory to create the repo in")
    create_parser.add_argument(
        'namespace', help=f"namespace to identify {ramble.repository.default_type.name} "
        "in the repository. defaults to the directory name", nargs='?')
    create_parser.add_argument(
        '-d', '--subdirectory',
        action='store',
        default=default_type_def['dir_name'],
        help=(
            "subdirectory to store applications in the repository. "
            f"Default '{default_type_def['dir_name']}'. Use an empty string for no subdirectory."
        ),
    )

    # List
    list_parser = sp.add_parser('list', help=repo_list.__doc__)
    list_parser.add_argument(
        '--scope', choices=scopes, metavar=scopes_metavar,
        default=ramble.config.default_list_scope(),
        help="configuration scope to read from")

    # Add
    add_parser = sp.add_parser('add', help=repo_add.__doc__)
    add_parser.add_argument(
        'path', help="path to a Ramble application repository directory")
    add_parser.add_argument(
        '--scope', choices=scopes, metavar=scopes_metavar,
        default=ramble.config.default_modify_scope(),
        help="configuration scope to modify")

    # Remove
    remove_parser = sp.add_parser(
        'remove', help=repo_remove.__doc__, aliases=['rm'])
    remove_parser.add_argument(
        'namespace_or_path',
        help="namespace or path of a Ramble application repository")
    remove_parser.add_argument(
        '--scope', choices=scopes, metavar=scopes_metavar,
        default=ramble.config.default_modify_scope(),
        help="configuration scope to modify")


def repo_create(args):
    """Create a new application repository."""
    full_path, namespace = ramble.repository.create_repo(
        args.directory, args.namespace, args.subdirectory
    )
    tty.msg("Created repo with namespace '%s'." % namespace)
    tty.msg("To register it with ramble, run this command:",
            'ramble repo add %s' % full_path)


def repo_add(args):
    """Add an application repository to Ramble's configuration."""
    path = args.path

    # real_path is absolute and handles substitution.
    canon_path = ramble.util.path.canonicalize_path(path)

    # check if the path exists
    if not os.path.exists(canon_path):
        tty.die("No such file or directory: %s" % path)

    # Make sure the path is a directory.
    if not os.path.isdir(canon_path):
        tty.die("Not a Ramble repository: %s" % path)

    # Make sure it's actually a ramble repository by constructing it.
    repo = ramble.repository.Repo(canon_path)

    # If that succeeds, finally add it to the configuration.
    repos = ramble.config.get('repos', scope=args.scope)
    if not repos:
        repos = []

    if repo.root in repos or path in repos:
        tty.die("Repository is already registered with Ramble: %s" % path)

    repos.insert(0, canon_path)
    ramble.config.set('repos', repos, args.scope)
    tty.msg("Added repo with namespace '%s'." % repo.namespace)


def repo_remove(args):
    """Remove a repository from Ramble's configuration."""
    repos = ramble.config.get('repos', scope=args.scope)
    namespace_or_path = args.namespace_or_path

    # If the argument is a path, remove that repository from config.
    canon_path = ramble.util.path.canonicalize_path(namespace_or_path)
    for repo_path in repos:
        repo_canon_path = ramble.util.path.canonicalize_path(repo_path)
        if canon_path == repo_canon_path:
            repos.remove(repo_path)
            ramble.config.set('repos', repos, args.scope)
            tty.msg("Removed repository %s" % repo_path)
            return

    # If it is a namespace, remove corresponding repo
    for path in repos:
        try:
            repo = ramble.repository.Repo(path)
            if repo.namespace == namespace_or_path:
                repos.remove(path)
                ramble.config.set('repos', repos, args.scope)
                tty.msg("Removed repository %s with namespace '%s'."
                        % (repo.root, repo.namespace))
                return
        except ramble.repository.RepoError:
            continue

    tty.die("No repository with path or namespace: %s"
            % namespace_or_path)


def repo_list(args):
    """Show registered repositories and their namespaces."""
    roots = ramble.config.get('repos', scope=args.scope)
    repos = []
    for r in roots:
        try:
            repos.append(ramble.repository.Repo(r))
        except ramble.repository.RepoError:
            continue

    if sys.stdout.isatty():
        msg = "%d application repositor" % len(repos)
        msg += "y." if len(repos) == 1 else "ies."
        tty.msg(msg)

    if not repos:
        return

    max_ns_len = max(len(r.namespace) for r in repos)
    for repo in repos:
        fmt = "%%-%ds%%s" % (max_ns_len + 4)
        print(fmt % (repo.namespace, repo.root))


def repo(parser, args):
    action = {'create': repo_create,
              'list': repo_list,
              'add': repo_add,
              'remove': repo_remove,
              'rm': repo_remove}
    action[args.repo_command](args)
