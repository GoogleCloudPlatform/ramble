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


def edit_object(name, obj_type_name, repo_path, namespace):
    """Opens the requested application file in your favorite $EDITOR.

    Args:
        name (str): The name of the application
        obj_type_name (str): Name of the object type to edit
        repo_path (str): The path to the repository containing this application
        namespace (str): A valid namespace registered with Ramble
    """
    obj_type = ramble.repository.ObjectTypes[obj_type_name]
    # Find the location of the package
    if repo_path:
        repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    elif namespace:
        repo = ramble.repository.paths[obj_type].get_repo(namespace)
    else:
        repo = ramble.repository.paths[obj_type]
    path = repo.filename_for_object_name(name)

    if os.path.exists(path):
        if not os.path.isfile(path):
            logger.die(f"Something is wrong. '{path}' is not a file!")
        if not os.access(path, os.R_OK):
            logger.die(f"Insufficient permissions on '{path}'!")
    else:
        # TODO: Update this once a `ramble create` command exists
        logger.die(
            f"No application for '{name}' was found."
            # "  Use `ramble create` to create a new application"
        )

    try:
        editor(path)
    except TypeError:
        logger.die("No valid editor was found.")


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


def object_exists(name, obj_type_name, repo_path=None, namespace=None):
    try:
        obj_type = ramble.repository.ObjectTypes[obj_type_name]
        if repo_path:
            repo = ramble.repository.Repo(repo_path, object_type=obj_type)
        elif namespace:
            repo = ramble.repository.paths[obj_type].get_repo(namespace)
        else:
            repo = ramble.repository.paths[obj_type]
        # Check if the filename for the object name exists
        path = repo.filename_for_object_name(name)
        return os.path.exists(path)
    except Exception:
        return False


def non_object_exists(name, type_name):
    type_to_path = {
        "test": ramble.paths.test_path,
        "command": ramble.paths.command_path,
        "docs": os.path.join(ramble.paths.lib_path, "docs"),
        "module": ramble.paths.module_path,
    }
    path = type_to_path[type_name]
    # convert command names to python module name
    if path == ramble.paths.command_path:
        name = ramble.cmd.python_name(name)

    path = os.path.join(path, name)
    if os.path.exists(path):
        return True

    # Otherwise do a glob check (excluding backups/pyc)
    files = glob.glob(path + ".*")
    exclude_list = [".pyc", "~"]
    files = list(filter(lambda x: all(s not in x for s in exclude_list), files))
    return len(files) > 0


def deduce_type(name, repo_path=None, namespace=None):
    # Try default type first (applications)
    default_type = ramble.repository.default_type.name
    if object_exists(name, default_type, repo_path, namespace):
        return default_type

    # Search all other object types
    for obj_type_name in ramble.repository.OBJECT_NAMES:
        if obj_type_name == default_type:
            continue
        if object_exists(name, obj_type_name, repo_path, namespace):
            return obj_type_name

    # Search non-object types
    for type_name in ["test", "command", "module", "docs"]:
        if non_object_exists(name, type_name):
            return type_name

    return None


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

    # By default, edit object files
    path = ramble.paths.builtin_path

    # Normalize input type if specified
    if args.type:
        args.type = normalize_type_name(args.type)

    if name and not args.type:
        detected_type = deduce_type(name, args.repo, args.namespace)
        if detected_type:
            args.type = detected_type

    # Default type if still not set
    if not args.type:
        args.type = ramble.repository.default_type.name

    # Map type arguments to paths if they aren't standard object types
    type_to_path = {
        "test": ramble.paths.test_path,
        "command": ramble.paths.command_path,
        "docs": os.path.join(ramble.paths.lib_path, "docs"),
        "module": ramble.paths.module_path,
    }

    if args.type in type_to_path:
        path = type_to_path[args.type]
        if name:
            # convert command names to python module name
            if path == ramble.paths.command_path:
                name = ramble.cmd.python_name(name)

            path = os.path.join(path, name)
            if not os.path.exists(path):
                files = glob.glob(path + ".*")
                exclude_list = [".pyc", "~"]  # exclude binaries and backups
                files = list(filter(lambda x: all(s not in x for s in exclude_list), files))
                if len(files) > 1:
                    m = f"Multiple files exist with the name {name}."
                    m += " Please specify a suffix. Files are:\n\n"
                    for f in files:
                        m += "        " + os.path.basename(f) + "\n"
                    logger.die(m)
                if not files:
                    logger.die(f"No file for '{name}' was found in {path}")
                path = files[0]  # already confirmed only one entry in files

        try:
            editor(path)
        except TypeError:
            logger.die("No valid editor was found.")
    elif name:
        edit_object(name, args.type, args.repo, args.namespace)
    else:
        # By default open the directory where applications live
        try:
            editor(path)
        except TypeError:
            logger.die("No valid editor was found.")
