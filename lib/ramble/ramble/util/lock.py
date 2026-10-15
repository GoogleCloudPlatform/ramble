# Copyright 2022-2026 The Ramble Authors
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
from llnl.util.lock import (
    LockError,
    LockTimeoutError,
    LockUpgradeError,
    ReadTransaction,
    WriteTransaction,
)

import ramble.config
import ramble.error


class Lock(llnl.util.lock.Lock):
    """Lock that can be disabled.

    This overrides the ``_lock()`` and ``_unlock()`` methods from
    ``llnl.util.lock`` so that all the lock API calls will succeed, but
    the actual locking mechanism can be disabled via ``_enable_locks``.
    """

    def __init__(
        self,
        path,
        start=0,
        length=0,
        default_timeout=None,
        debug=False,
        desc="",
        enable=None,
        **kwargs,
    ):
        self._enable = ramble.config.get("config:locks", True)
        if enable is None:
            enable = self._enable

        super().__init__(
            path,
            start=start,
            length=length,
            default_timeout=default_timeout,
            debug=debug,
            desc=desc,
            enable=enable,
            **kwargs,
        )

    def __del__(self):
        # Clean up file descriptor leaks in llnl.util.lock.Lock by releasing
        # the file tracker reference when the lock is garbage collected.
        try:
            if hasattr(self, "backend"):
                backend = self.backend
                file_ref = getattr(backend, "_file_ref", None)
                if file_ref is not None:
                    import llnl.util.lock

                    llnl.util.lock.FILE_TRACKER.release(file_ref)
                    backend._file_ref = None  # type: ignore[union-attr]
        except Exception:
            pass


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


__all__ = [
    "LockError",
    "LockTimeoutError",
    "LockUpgradeError",
    "ReadTransaction",
    "WriteTransaction",
    "Lock",
    "check_lock_safety",
]
