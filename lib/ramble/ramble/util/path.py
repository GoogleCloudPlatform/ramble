# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Utilities for managing paths in ramble.

TODO: this is really part of ramble.config. Consolidate it.
"""

import getpass
import os
import re
import tempfile
import urllib.parse

import ramble.paths

__all__ = ["substitute_config_variables", "substitute_path_variables", "canonicalize_path"]

# Substitutions to perform
replacements = {
    "ramble": ramble.paths.prefix,
    "user": getpass.getuser(),
    "tempdir": tempfile.gettempdir(),
}


def substitute_config_variables(path, local_replacements):
    """Substitute placeholders into paths.

    Ramble allows paths in configs to have some placeholders, as follows:

    - $ramble    The ramble instance's prefix
    - $user      The current user's username
    - $tempdir   Default temporary directory returned by tempfile.gettempdir()

    These are substituted case-insensitively into the path, and users can
    use either ``$var`` or ``${var}`` syntax for the variables.

    """

    # Look up replacements for re.sub in the replacements dict.
    def repl(match):
        m = match.group(0).strip("${}")
        lower_key = m.lower()
        return replacements.get(lower_key, local_replacements.get(lower_key, match.group(0)))

    # Replace $var or ${var}.
    return re.sub(r"(\$\w+\b|\$\{\w+\})", repl, path)


def substitute_path_variables(path, local_replacements=None):
    """Substitute config vars, expand environment vars, expand user home."""
    if local_replacements is None:
        local_replacements = {}
    path = substitute_config_variables(path, local_replacements)
    path = os.path.expandvars(path)
    path = os.path.expanduser(path)
    return path


def canonicalize_path(path):
    """Same as substitute_path_variables, but also take absolute path."""
    path = substitute_path_variables(path)
    path = os.path.abspath(path)

    return path


def normalize_path_or_url(path):
    """Convert a scheme-less path to absolute local path
    Also, remove trailing back-slashes from the input path

    Args:
        path (str): Input path

    Returns:
        (str): Absolute local path or cleaned remote url
    """

    # Remove trailing back-slashes from path
    real_path = path.rstrip("/")

    parsed = urllib.parse.urlparse(real_path)
    if not parsed.scheme:
        return os.path.abspath(real_path)
    return real_path
