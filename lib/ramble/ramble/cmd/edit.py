# Copyright 2022-2024 The Ramble Authors
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
    subparser.add_argument(
        "--type",
        default=f"{ramble.repository.default_type.name}",
        help=f"Type of object to edit. Defaults to '{ramble.repository.default_type.name}'. "
        f"Allowed types are {', '.join(ramble.repository.OBJECT_NAMES)}",
    )

    excl_args = subparser.add_mutually_exclusive_group()

    # Various types of Ramble files that can be edited
    excl_args.add_argument(
        "-c",
        "--command",
        dest="path",
        action="store_const",
        const=ramble.paths.command_path,
        help="edit the command with the supplied name",
    )
    excl_args.add_argument(
        "-d",
        "--docs",
        dest="path",
        action="store_const",
        const=os.path.join(ramble.paths.lib_path, "docs"),
        help="edit the docs with the supplied name",
    )
    excl_args.add_argument(
        "-t",
        "--test",
        dest="path",
        action="store_const",
        const=ramble.paths.test_path,
        help="edit the test with the supplied name",
    )
    excl_args.add_argument(
        "-m",
        "--module",
        dest="path",
        action="store_const",
        const=ramble.paths.module_path,
        help="edit the main ramble module with the supplied name",
    )

    # Options for editing applications
    excl_args.add_argument("-r", "--repo", default=None, help="path to repo to edit object in")
    excl_args.add_argument("-N", "--namespace", default=None, help="namespace of object to edit")

    subparser.add_argument("object_name", nargs="?", default=None, help="object name")


def edit(parser, args):
    name = args.object_name

    # By default, edit object files
    path = ramble.paths.builtin_path

    # If `--command`, `--test`, or `--module` is chosen, edit those instead
    if args.path:
        path = args.path
        if name:
            # convert command names to python module name
            if path == ramble.paths.command_path:
                name = ramble.cmd.python_name(name)

            path = os.path.join(path, name)
            if not os.path.exists(path):
                files = glob.glob(path + "*")
                blacklist = [".pyc", "~"]  # blacklist binaries and backups
                files = list(filter(lambda x: all(s not in x for s in blacklist), files))
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
