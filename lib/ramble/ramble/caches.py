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
