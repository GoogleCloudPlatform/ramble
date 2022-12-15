# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import sys

import pytest

from llnl.util.filesystem import mkdirp, touch

import spack.config
from spack.fetch_strategy import CacheURLFetchStrategy, NoCacheError
from spack.stage import Stage

is_windows = sys.platform == 'win32'


@pytest.mark.parametrize('_fetch_method', ['curl', 'urllib'])
def test_fetch_missing_cache(tmpdir, _fetch_method):
    """Ensure raise a missing cache file."""
    testpath = str(tmpdir)
    with spack.config.override('config:url_fetch_method', _fetch_method):
        abs_pref = '' if is_windows else '/'
        url = 'file://' + abs_pref + 'not-a-real-cache-file'
        fetcher = CacheURLFetchStrategy(url=url)
        with Stage(fetcher, path=testpath):
            with pytest.raises(NoCacheError, match=r'No cache'):
                fetcher.fetch()


@pytest.mark.parametrize('_fetch_method', ['curl', 'urllib'])
def test_fetch(tmpdir, _fetch_method):
    """Ensure a fetch after expanding is effectively a no-op."""
    testpath = str(tmpdir)
    cache = os.path.join(testpath, 'cache.tar.gz')
    touch(cache)
    if is_windows:
        url_stub = '{0}'
    else:
        url_stub = '/{0}'
    url = 'file://' + url_stub.format(cache)
    with spack.config.override('config:url_fetch_method', _fetch_method):
        fetcher = CacheURLFetchStrategy(url=url)
        with Stage(fetcher, path=testpath) as stage:
            source_path = stage.source_path
            mkdirp(source_path)
            fetcher.fetch()
