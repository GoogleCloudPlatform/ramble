# Copyright 2022-2024 The Ramble Authors
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
        workspace (Workspace): A ramble workspace

    Returns:
        (str): A file path
    """
    if not workspace.dry_run or is_dry_run_path(path):
        return path
    return os.path.join(_DRY_RUN_PATH_PREFIX, os.path.relpath(path))


def is_dry_run_path(path: str) -> bool:
    """Check if the path is already a dry_run path"""
    return path.startswith(_DRY_RUN_PATH_PREFIX)
