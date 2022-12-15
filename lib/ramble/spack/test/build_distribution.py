# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import os.path
import sys

import pytest

import spack.binary_distribution
import spack.spec

install = spack.main.SpackCommand('install')

pytestmark = pytest.mark.skipif(sys.platform == "win32",
                                reason="does not run on windows")


def _validate_url(url):
    return


@pytest.fixture(autouse=True)
def url_check(monkeypatch):
    monkeypatch.setattr(spack.util.url, 'require_url_format', _validate_url)


def test_build_tarball_overwrite(
        install_mockery, mock_fetch, monkeypatch, tmpdir):

    with tmpdir.as_cwd():
        spec = spack.spec.Spec('trivial-install-test-package').concretized()
        install(str(spec))

        # Runs fine the first time, throws the second time
        spack.binary_distribution._build_tarball(spec, '.', unsigned=True)
        with pytest.raises(spack.binary_distribution.NoOverwriteException):
            spack.binary_distribution._build_tarball(spec, '.', unsigned=True)

        # Should work fine with force=True
        spack.binary_distribution._build_tarball(spec, '.', force=True, unsigned=True)

        # Remove the tarball and try again.
        # This must *also* throw, because of the existing .spec.json file
        os.remove(os.path.join(
            spack.binary_distribution.build_cache_prefix('.'),
            spack.binary_distribution.tarball_directory_name(spec),
            spack.binary_distribution.tarball_name(spec, '.spack')))

        with pytest.raises(spack.binary_distribution.NoOverwriteException):
            spack.binary_distribution._build_tarball(spec, '.', unsigned=True)
