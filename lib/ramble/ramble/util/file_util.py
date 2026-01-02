# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from pathlib import Path

_DRY_RUN_PATH_PREFIX = os.path.join("dry-run", "path", "to")


def get_file_path(path: str, workspace) -> str:
    """A wrapper for file paths used in a Ramble application, to facilitate testing.

    Args:
        path (str): A file path
        workspace (ramble.workspace.Workspace): A ramble workspace

    Returns:
        (str): A file path
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
        (str): Path to newest file (or None if not found)
        (int): Timestamp of file in seconds (or None if no file is found)
    """
    files = Path(base_directory).rglob("*")
    files = [f for f in files if f.is_file() and not os.path.basename(f).startswith("ramble_")]

    if not files:
        return None, None

    newest_file_path = max(files, key=os.path.getmtime)

    timestamp_seconds = os.path.getmtime(newest_file_path)

    return str(newest_file_path), timestamp_seconds
