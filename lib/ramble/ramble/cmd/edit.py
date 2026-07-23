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


def setup_parser(subparser):
    # Edits object (application) files by default
    extra_types = ["test", "command", "docs", "module"]
    allowed_types = ramble.repository.OBJECT_NAMES + extra_types
    subparser.add_argument(
        "-t",
        "--type",
        default=f"{ramble.repository.default_type.name}",
        help=f"Type of object to edit. Defaults to '{ramble.repository.default_type.name}'. "
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

    # Map type arguments to paths if they aren't standard object types
    type_to_path = {
        "test": ramble.paths.test_path,
        "tests": ramble.paths.test_path,
        "command": ramble.paths.command_path,
        "commands": ramble.paths.command_path,
        "docs": os.path.join(ramble.paths.lib_path, "docs"),
        "doc": os.path.join(ramble.paths.lib_path, "docs"),
        "module": ramble.paths.module_path,
        "modules": ramble.paths.module_path,
    }

    if args.type in type_to_path:
        path = type_to_path[args.type]
        if name:
            # convert command names to python module name
            if path == ramble.paths.command_path:
                name = ramble.cmd.python_name(name)

            path = os.path.join(path, name)
            if not os.path.exists(path):
                files = glob.glob(path + "*")
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
