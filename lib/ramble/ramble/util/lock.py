# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Wrapper for ``llnl.util.lock`` allows locking to be enabled/disabled."""
import os
import stat

import llnl.util.lock
from llnl.util.lock import *  # noqa

import ramble.config
import ramble.error
import ramble.paths


class Lock(llnl.util.lock.Lock):
    """Lock that can be disabled.

    This overrides the ``_lock()`` and ``_unlock()`` methods from
    ``llnl.util.lock`` so that all the lock API calls will succeed, but
    the actual locking mechanism can be disabled via ``_enable_locks``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enable = ramble.config.get("config:locks", True)

    def _lock(self, op, timeout=0):
        if self._enable:
            return super()._lock(op, timeout)
        else:
            return 0, 0

    def _unlock(self):
        """Unlock call that always succeeds."""
        if self._enable:
            super()._unlock()

    def _debug(self, *args):
        if self._enable:
            super()._debug(*args)

    def cleanup(self, *args):
        if self._enable:
            super().cleanup(*args)


def check_lock_safety(path):
    """Do some extra checks to ensure disabling locks is safe.

    This will raise an error if ``path`` can is group- or world-writable
    AND the current user can write to the directory (i.e., if this user
    AND others could write to the path).

    This is intended to run on the Ramble prefix, but can be run on any
    path for testing.
    """
    if os.access(path, os.W_OK):
        stat_result = os.stat(path)
        uid, gid = stat_result.st_uid, stat_result.st_gid
        mode = stat_result[stat.ST_MODE]

        writable = None
        if (mode & stat.S_IWGRP) and (uid != gid):
            # ramble is group-writeable and the group is not the owner
            writable = "group"
        elif mode & stat.S_IWOTH:
            # ramble is world-writeable
            writable = "world"

        if writable:
            msg = f"Refusing to disable locks: ramble is {writable}-writable."
            long_msg = (
                "Running a shared ramble without locks is unsafe. You must "
                "restrict permissions on {} or enable locks."
            ).format(path)
            raise ramble.error.RambleError(msg, long_msg)
