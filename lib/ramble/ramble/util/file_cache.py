# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import contextlib
import os
import shutil

from llnl.util.filesystem import mkdirp

from ramble.error import RambleError
from ramble.util.lock import Lock


class FileCache:
    """This class manages cached data in the filesystem.

    - Cache files are fetched and stored by unique keys.  Keys can be relative
      paths, so that there can be some hierarchy in the cache.

    - The FileCache handles locking cache files for reading and writing, so
      client code need not manage locks for cache entries.

    """

    def __init__(self, root, timeout=120):
        """Create a file cache object.

        This will create the cache directory if it does not exist yet.

        Args:
            root: specifies the root directory where the cache stores files

            timeout: when there is contention among multiple Ramble processes
                for cache files, this specifies how long Ramble should wait
                before assuming that there is a deadlock.
        """
        self.root = root.rstrip(os.path.sep)
        if not os.path.exists(self.root):
            mkdirp(self.root)

        self._locks = {}
        self.lock_timeout = timeout

    def destroy(self):
        """Remove all files under the cache root."""
        for f in os.listdir(self.root):
            path = os.path.join(self.root, f)
            if os.path.isdir(path):
                shutil.rmtree(path, True)
            else:
                os.remove(path)

    def cache_path(self, key):
        """Path to the file in the cache for a particular key."""
        return os.path.join(self.root, key)

    def _lock_path(self, key):
        """Path to the file in the cache for a particular key."""
        keyfile = os.path.basename(key)
        keydir = os.path.dirname(key)

        return os.path.join(self.root, keydir, "." + keyfile + ".lock")

    def _get_lock(self, key):
        """Create a lock for a key, if necessary, and return a lock object."""
        if key not in self._locks:
            self._locks[key] = Lock(self._lock_path(key), default_timeout=self.lock_timeout)
        return self._locks[key]

    def init_entry(self, key):
        """Ensure we can access a cache file. Create a lock for it if needed.

        Return whether the cache file exists yet or not.
        """
        cache_path = self.cache_path(key)

        exists = os.path.exists(cache_path)
        if exists:
            if not os.path.isfile(cache_path):
                raise CacheError(f"Cache file is not a file: {cache_path}")

            if not os.access(cache_path, os.R_OK | os.W_OK):
                raise CacheError(f"Cannot access cache file: {cache_path}")
        else:
            # if the file is hierarchical, make parent directories
            parent = os.path.dirname(cache_path)
            if parent.rstrip(os.path.sep) != self.root:
                mkdirp(parent)

            if not os.access(parent, os.R_OK | os.W_OK):
                raise CacheError(f"Cannot access cache directory: {parent}")

            # ensure lock is created for this key
            self._get_lock(key)
        return exists

    @contextlib.contextmanager
    def read_transaction(self, key):
        """Get a read transaction on a file cache item.

        Returns a ReadTransaction context manager and opens the cache file for
        reading.  You can use it like this:

           with file_cache_object.read_transaction(key) as cache_file:
               cache_file.read()

        """
        lock = self._get_lock(key)
        lock.acquire_read()
        try:
            with open(self.cache_path(key), encoding="utf-8") as f:
                yield f
        finally:
            lock.release_read()

    @contextlib.contextmanager
    def write_transaction(self, key):
        """Get a write transaction on a file cache item.

        Returns a WriteTransaction context manager that opens a temporary file
        for writing.  Once the context manager finishes, if nothing went wrong,
        moves the file into place on top of the old file atomically.

        """
        lock = self._get_lock(key)
        lock.acquire_write()
        try:
            orig_filename = self.cache_path(key)
            orig_file = None
            if os.path.exists(orig_filename):
                orig_file = open(orig_filename, encoding="utf-8")

            tmp_filename = self.cache_path(key) + ".tmp"
            tmp_file = open(tmp_filename, "w", encoding="utf-8")

            try:
                yield orig_file, tmp_file
            except Exception:
                if orig_file:
                    orig_file.close()
                tmp_file.close()
                os.remove(tmp_filename)
                raise
            else:
                if orig_file:
                    orig_file.close()
                tmp_file.close()
                os.rename(tmp_filename, orig_filename)
        finally:
            lock.release_write()

    def mtime(self, key):
        """Return modification time of cache file, or 0 if it does not exist.

        Time is in units returned by os.stat in the mtime field, which is
        platform-dependent.

        """
        if not self.init_entry(key):
            return 0
        else:
            sinfo = os.stat(self.cache_path(key))
            return sinfo.st_mtime

    def remove(self, key):
        lock = self._get_lock(key)
        try:
            lock.acquire_write()
            os.unlink(self.cache_path(key))
        finally:
            lock.release_write()
        os.unlink(self._lock_path(key))


class CacheError(RambleError):
    pass
