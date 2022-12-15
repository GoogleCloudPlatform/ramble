# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import sys

import pytest

import spack.caches
import spack.main
import spack.package
import spack.stage

clean = spack.main.SpackCommand('clean')

pytestmark = pytest.mark.skipif(sys.platform == "win32",
                                reason="does not run on windows")


@pytest.fixture()
def mock_calls_for_clean(monkeypatch):

    counts = {}

    class Counter(object):
        def __init__(self, name):
            self.name = name
            counts[name] = 0

        def __call__(self, *args, **kwargs):
            counts[self.name] += 1

    monkeypatch.setattr(spack.package.PackageBase, 'do_clean',
                        Counter('package'))
    monkeypatch.setattr(spack.stage, 'purge', Counter('stages'))
    monkeypatch.setattr(
        spack.caches.fetch_cache, 'destroy', Counter('downloads'),
        raising=False)
    monkeypatch.setattr(
        spack.caches.misc_cache, 'destroy', Counter('caches'))
    monkeypatch.setattr(
        spack.installer, 'clear_failures', Counter('failures'))

    yield counts


all_effects = ['stages', 'downloads', 'caches', 'failures']


@pytest.mark.usefixtures(
    'mock_packages', 'config'
)
@pytest.mark.parametrize('command_line,effects', [
    ('mpileaks', ['package']),
    ('-s',       ['stages']),
    ('-sd',      ['stages', 'downloads']),
    ('-m',       ['caches']),
    ('-f',       ['failures']),
    ('-a',       all_effects),
    ('',         []),
])
def test_function_calls(command_line, effects, mock_calls_for_clean):

    # Call the command with the supplied command line
    clean(command_line)

    # Assert that we called the expected functions the correct
    # number of times
    for name in ['package'] + all_effects:
        assert mock_calls_for_clean[name] == (1 if name in effects else 0)
