# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.config
import ramble.fetch_strategy
import ramble.stage


@pytest.mark.parametrize("_fetch_method", ["curl", "urllib"])
def test_gcsfetchstrategy_without_url(_fetch_method):
    """Ensure constructor with no URL fails."""
    with ramble.config.override("config:url_fetch_method", _fetch_method):
        with pytest.raises(ValueError):
            ramble.fetch_strategy.GCSFetchStrategy(None)


@pytest.mark.parametrize("_fetch_method", ["curl", "urllib"])
def test_gcsfetchstrategy_bad_url(tmpdir, _fetch_method):
    """Ensure fetch with bad URL fails as expected."""
    testpath = str(tmpdir)

    with ramble.config.override("config:url_fetch_method", _fetch_method):
        fetcher = ramble.fetch_strategy.GCSFetchStrategy(url="file:///does-not-exist")
        assert fetcher is not None

        with ramble.stage.InputStage(fetcher, name="test", path=testpath) as stage:
            assert stage is not None
            assert fetcher.archive_file is None
            with pytest.raises(ramble.fetch_strategy.FetchError):
                fetcher.fetch()


@pytest.mark.parametrize("_fetch_method", ["curl", "urllib"])
def test_gcsfetchstrategy_downloaded(tmpdir, _fetch_method):
    """Ensure fetch with archive file already downloaded is a noop."""
    testpath = str(tmpdir)
    archive = os.path.join(testpath, "gcs.tar.gz")

    with ramble.config.override("config:url_fetch_method", _fetch_method):

        class Archived_GCSFS(ramble.fetch_strategy.GCSFetchStrategy):
            @property
            def archive_file(self):
                return archive

        url = f"gcs:///{archive}"
        fetcher = Archived_GCSFS(url=url)
        with ramble.stage.InputStage(fetcher, name="test", path=testpath):
            fetcher.fetch()


@pytest.mark.parametrize("_fetch_method", ["curl", "urllib"])
def test_gcsfetchstrategy_download(tmpdir, _fetch_method):
    """Ensure fetch of fie."""

    google_api_core_exceptions = pytest.importorskip("google.api_core.exceptions")
    google_auth_exceptions = pytest.importorskip("google.auth.exceptions")
    try:
        testpath = str(tmpdir)
        path = "gs://hpc-toolkit-demos/build_cache/index.json"

        with ramble.config.override("config:url_fetch_method", _fetch_method):
            fetcher = ramble.fetch_strategy.GCSFetchStrategy(url=path)
            with ramble.stage.InputStage(fetcher, name="test", path=testpath):
                fetcher.fetch()
    except google_api_core_exceptions.Forbidden as e:
        pytest.skip("%s" % e)
    except google_auth_exceptions.RefreshError as e:
        pytest.skip("%s" % e)
    except google_auth_exceptions.DefaultCredentialsError as e:
        pytest.skip("%s" % e)
