# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

_DRY_RUN_PATH_PREFIX = os.path.join("dry-run", "path", "to")


def get_file_path(path: str, workspace) -> str:
    """A wrapper for file paths used in a Ramble application, to facilitate testing.

    Args:
        path (str): A file path
        workspace (ramble.workspace.Workspace): A ramble workspace

    Returns:
        str: A file path
    """
    if not workspace.dry_run or is_dry_run_path(path):
        return path
    return os.path.join(_DRY_RUN_PATH_PREFIX, os.path.relpath(path))


def is_dry_run_path(path: str) -> bool:
    """Check if the path is already a dry_run path"""
    return str(path).startswith(_DRY_RUN_PATH_PREFIX)


def create_symlink(base, link):
    """
    Create symlink of a file to give a known and predictable path
    """
    if os.path.islink(link):
        os.unlink(link)

    os.symlink(base, link)


def get_newest_experiment_file(base_directory):
    """Given a base directory, determine the newest file in the directory (and
    it's subdirectories)and return the file path and it's timestamp in seconds.

    Args:
        base_directory (str): Directory to search newest file for

    Returns:
        str | None: Path to newest file (or None if not found)
        int | None: Timestamp of file in seconds (or None if no file is found)
    """
    newest_file = None
    max_mtime = -1.0

    stack = [base_directory]

    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    try:
                        if entry.is_file():
                            if not entry.name.startswith("ramble_"):
                                mtime = entry.stat().st_mtime
                                if mtime > max_mtime:
                                    max_mtime = mtime
                                    newest_file = entry.path
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except FileNotFoundError:
                        # File was deleted concurrently
                        continue
        except FileNotFoundError:
            continue

    if newest_file is None:
        return None, None

    return newest_file, max_mtime
