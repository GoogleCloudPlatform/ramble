# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import glob
import os

import ramble.cmd
import ramble.paths
import ramble.repository
from ramble.util.logger import logger

from spack.util.editor import editor

description = "open application files in $EDITOR"
section = "application dev"
level = "short"


def normalize_type_name(type_name):
    if not type_name:
        return None

    # Map aliases
    aliases = {
        "test": "test",
        "tests": "test",
        "command": "command",
        "commands": "command",
        "docs": "docs",
        "doc": "docs",
        "module": "module",
        "modules": "module",
    }
    if type_name in aliases:
        return aliases[type_name]

    # Map singular to plural for ObjectTypes
    norm_type = type_name.lower().replace("-", " ").replace("_", " ")
    for obj_type in ramble.repository.ObjectTypes:
        if norm_type == obj_type.name.lower().replace("_", " "):
            return obj_type.name
        if obj_type in ramble.repository.type_definitions:
            singular = ramble.repository.type_definitions[obj_type]["singular"]
            if norm_type == singular.lower().replace("_", " ").replace("-", " "):
                return obj_type.name

    return type_name


def find_all_matches(name, repo_path=None, namespace=None, obj_type=None):
    """Find all potential file paths that match the given name.

    Returns a list of dictionaries with keys:
    - 'type': type of object/file
    - 'path': path of the file
    - 'repo_namespace': namespace of the repository (if applicable, else None)
    """
    matches = []

    extra_types = ["test", "command", "docs", "module"]
    allowed_types = ramble.repository.OBJECT_NAMES + extra_types

    types_to_check = [obj_type] if obj_type else allowed_types

    for t in types_to_check:
        if t in ramble.repository.OBJECT_NAMES:
            # Check object type
            obj_type = ramble.repository.ObjectTypes[t]
            if repo_path:
                try:
                    repos = [ramble.repository.Repo(repo_path, object_type=obj_type)]
                except Exception:
                    repos = []
            elif namespace:
                try:
                    repos = [ramble.repository.paths[obj_type].get_repo(namespace)]
                except Exception:
                    repos = []
            else:
                repos = ramble.repository.paths[obj_type].repos

            for repo in repos:
                path = repo.filename_for_object_name(name)
                if os.path.isfile(path):
                    matches.append({"type": t, "path": path, "repo_namespace": repo.namespace})
        elif t in extra_types:
            # Check non-object type
            if repo_path or namespace:
                continue

            type_to_path = {
                "test": ramble.paths.test_path,
                "command": ramble.paths.command_path,
                "docs": os.path.join(ramble.paths.lib_path, "docs"),
                "module": ramble.paths.module_path,
            }
            path = type_to_path[t]
            if t == "command":
                name_file = ramble.cmd.python_name(name)
            else:
                name_file = name

            full_path = os.path.join(path, name_file)
            if os.path.isfile(full_path):
                matches.append({"type": t, "path": full_path, "repo_namespace": None})
            else:
                # Do a glob check (excluding backups/pyc)
                files = glob.glob(full_path + ".*")
                exclude_list = [".pyc", "~"]
                files = list(
                    filter(
                        lambda x: os.path.isfile(x) and all(s not in x for s in exclude_list),
                        files,
                    )
                )
                matches.extend({"type": t, "path": f, "repo_namespace": None} for f in files)

    return matches


def setup_parser(subparser):
    # Edits object (application) files by default
    extra_types = ["test", "command", "docs", "module"]
    allowed_types = ramble.repository.OBJECT_NAMES + extra_types
    subparser.add_argument(
        "-t",
        "--type",
        default=None,
        help="Type of object to edit. Defaults to automatic deduction with fallback to "
        f"'{ramble.repository.default_type.name}'. "
        f"Allowed types are {', '.join(allowed_types)}",
    )

    excl_args = subparser.add_mutually_exclusive_group()

    # Options for editing applications
    excl_args.add_argument("-r", "--repo", default=None, help="path to repo to edit object in")
    excl_args.add_argument("-N", "--namespace", default=None, help="namespace of object to edit")

    subparser.add_argument("object_name", nargs="?", default=None, help="object name")


def edit(parser, args):
    name = args.object_name

    # Normalize input type if specified
    if args.type:
        args.type = normalize_type_name(args.type)
        extra_types = ["test", "command", "docs", "module"]
        allowed_types = ramble.repository.OBJECT_NAMES + extra_types
        if args.type not in allowed_types:
            # Trigger KeyError like the original code did
            _ = ramble.repository.ObjectTypes[args.type]

    if name:
        matches = find_all_matches(name, args.repo, args.namespace, args.type)

        if len(matches) >= 1:
            if len(matches) > 1:
                # Check if all matches are of the same non-object type (glob search matches)
                # which means they are just different suffixes for the same name/type
                first_match_type = matches[0]["type"]
                extra_types = ["test", "command", "docs", "module"]
                if first_match_type in extra_types and all(
                    m["type"] == first_match_type for m in matches
                ):
                    m = f"Multiple files exist with the name {name}."
                    m += " Please specify a suffix. Files are:\n\n"
                    for match in matches:
                        m += "        " + os.path.basename(match["path"]) + "\n"
                    logger.die(m)

                m = (
                    f"Multiple matches found for '{name}'. "
                    f"Opening highest-precedence match:\n  {matches[0]['path']}\n"
                )
                m += "In order to open a different object, use the commands below:\n"
                for match in matches[1:]:
                    if match["repo_namespace"]:
                        m += (
                            f"  Type: {match['type']}, "
                            f"Command: ramble edit --type {match['type']} "
                            f"--namespace {match['repo_namespace']} {name}\n"
                        )
                    else:
                        m += (
                            f"  Type: {match['type']}, "
                            f"Command: ramble edit --type {match['type']} {name}\n"
                        )
                logger.warn(m)

            path = matches[0]["path"]
            if not os.access(path, os.R_OK):
                logger.die(f"Insufficient permissions on '{path}'!")

            try:
                editor(path)
            except TypeError:
                logger.die("No valid editor was found.")
            return

        # If no matches found, reproduce the original behavior/messages:
        # 1. If type is specified/defaulted, we show type-specific "not found" messages.
        type_name = args.type or ramble.repository.default_type.name
        type_to_path = {
            "test": ramble.paths.test_path,
            "command": ramble.paths.command_path,
            "docs": os.path.join(ramble.paths.lib_path, "docs"),
            "module": ramble.paths.module_path,
        }

        if type_name in type_to_path:
            path = type_to_path[type_name]
            if type_name == "command":
                name = ramble.cmd.python_name(name)
            path = os.path.join(path, name)
            logger.die(f"No file for '{name}' was found in {path}")
        else:
            # It's an object type. Let's find what path it would have been at.
            try:
                obj_type = ramble.repository.ObjectTypes[type_name]
                if args.repo:
                    repo = ramble.repository.Repo(args.repo, object_type=obj_type)
                elif args.namespace:
                    repo = ramble.repository.paths[obj_type].get_repo(args.namespace)
                else:
                    repo = ramble.repository.paths[obj_type]
                path = repo.filename_for_object_name(name)
            except Exception:
                path = None

            if path and os.path.exists(path):
                if not os.path.isfile(path):
                    logger.die(f"Something is wrong. '{path}' is not a file!")

            # Print standard error message
            if type_name == ramble.repository.default_type.name:
                logger.die(f"No application for '{name}' was found.")
            else:
                # For other object types, print a generic not found message
                logger.die(f"No {type_name} for '{name}' was found.")
    else:
        # By default, open the directory where applications live
        path = ramble.paths.builtin_path
        if args.type:
            type_to_path = {
                "test": ramble.paths.test_path,
                "command": ramble.paths.command_path,
                "docs": os.path.join(ramble.paths.lib_path, "docs"),
                "module": ramble.paths.module_path,
            }
            if args.type in type_to_path:
                path = type_to_path[args.type]
            else:
                try:
                    obj_type = ramble.repository.ObjectTypes[args.type]
                    if args.repo:
                        repo = ramble.repository.Repo(args.repo, object_type=obj_type)
                    elif args.namespace:
                        repo = ramble.repository.paths[obj_type].get_repo(args.namespace)
                    else:
                        repo = ramble.repository.paths[obj_type]
                    # Default path to the repo root/objects folder
                    path = repo.objects_path
                except Exception:
                    pass

        try:
            editor(path)
        except TypeError:
            logger.die("No valid editor was found.")
