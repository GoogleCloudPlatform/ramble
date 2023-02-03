# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Caches used by Ramble to store data"""
import os

import llnl.util.lang
from llnl.util.filesystem import mkdirp
from llnl.util.symlink import symlink

import ramble.error
import ramble.paths
import ramble.config
import ramble.util.file_cache
import ramble.util.path


def _misc_cache():
    """The ``misc_cache`` is rambles's cache for small data.

    Currently the ``misc_cache`` stores indexes for virtual dependency
    providers and for which packages provide which tags.
    """
    path = ramble.config.get('config:misc_cache')
    if not path:
        path = os.path.join(ramble.paths.user_config_path, 'cache')
    path = ramble.util.path.canonicalize_path(path)

    return ramble.util.file_cache.FileCache(path)


#: Ramble's cache for small data
misc_cache = llnl.util.lang.Singleton(_misc_cache)


def fetch_cache_location():
    """Filesystem cache of downloaded archives.

    This prevents Ramble from repeatedly fetch the same files when
    using them within multiple workspaces.
    """
    path = ramble.config.get('config:input_cache')
    if not path:
        path = ramble.paths.default_fetch_cache_path
    path = ramble.util.path.canonicalize_path(path)
    return path


def _fetch_cache():
    path = fetch_cache_location()
    return ramble.fetch_strategy.FsCache(path)


class MirrorCache(object):
    def __init__(self, root, skip_unstable_versions):
        self.root = os.path.abspath(root)
        self.skip_unstable_versions = skip_unstable_versions

    def store(self, fetcher, relative_dest):
        """Fetch and relocate the fetcher's target into our mirror cache."""

        # Note this will archive package sources even if they would not
        # normally be cached (e.g. the current tip of an hg/git branch)
        dst = os.path.join(self.root, relative_dest)
        mkdirp(os.path.dirname(dst))
        fetcher.archive(dst)

    def symlink(self, mirror_ref):
        """Symlink a human readible path in our mirror to the actual
        storage location."""

        cosmetic_path = os.path.join(self.root, mirror_ref.cosmetic_path)
        storage_path = os.path.join(self.root, mirror_ref.storage_path)
        relative_dst = os.path.relpath(
            storage_path,
            start=os.path.dirname(cosmetic_path))

        if not os.path.exists(cosmetic_path):
            if os.path.lexists(cosmetic_path):
                # In this case the link itself exists but it is broken: remove
                # it and recreate it (in order to fix any symlinks broken prior
                # to https://github.com/spack/spack/pull/13908)
                os.unlink(cosmetic_path)
            mkdirp(os.path.dirname(cosmetic_path))
            symlink(relative_dst, cosmetic_path)


#: Ramble's local cache for downloaded source archives
fetch_cache = llnl.util.lang.Singleton(_fetch_cache)
