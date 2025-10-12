# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the fetch_strategy functions"""
import os
import shutil
from unittest import mock

import pytest

from ramble import fetch_strategy
from ramble.fetch_strategy import FailedDownloadError


@pytest.mark.parametrize(
    "url,expected_fetcher_type",
    [
        ("file://my-path", fetch_strategy.URLFetchStrategy),
        ("https://my-url", fetch_strategy.URLFetchStrategy),
        ("gs://my-bucket", fetch_strategy.GCSFetchStrategy),
        ("s3://my-bucket", fetch_strategy.S3FetchStrategy),
    ],
)
def test_from_url_scheme(url, expected_fetcher_type):
    fetcher = fetch_strategy.from_url_scheme(url)
    assert isinstance(fetcher, expected_fetcher_type)


def test_bad_from_url_scheme():
    with pytest.raises(ValueError, match="No FetchStrategy found"):
        fetch_strategy.from_url_scheme("unknown://my-url")


class TestFsCache:
    def test_store_uncachable(self, tmp_path):
        """Test that store does nothing for an uncachable fetcher."""
        cache = fetch_strategy.FsCache(str(tmp_path))
        # No digest, so uncachable
        fetcher = fetch_strategy.URLFetchStrategy(url="http://example.com")

        fetcher.archive = mock.Mock()

        cache.store(fetcher, "dest/file")

        fetcher.archive.assert_not_called()
        assert not (tmp_path / "dest").exists()

    def test_store_already_cached(self, tmp_path):
        """Test that store does nothing for an already cached fetcher."""
        cache = fetch_strategy.FsCache(str(tmp_path))
        fetcher = fetch_strategy.CacheURLFetchStrategy(url="file:///path/to/cache")

        fetcher.archive = mock.Mock()

        cache.store(fetcher, "dest/file")

        fetcher.archive.assert_not_called()
        assert not (tmp_path / "dest").exists()

    def test_store_cachable_and_destroy(self, tmp_path):
        """Test that store caches a cachable fetcher and destroy works."""
        cache = fetch_strategy.FsCache(str(tmp_path))
        fetcher = fetch_strategy.URLFetchStrategy(url="http://example.com", checksum="sha256:123")

        fetcher.archive = mock.Mock()

        dest_path = "dest/file"
        cache.store(fetcher, dest_path)

        expected_dst = os.path.join(str(tmp_path), dest_path)
        fetcher.archive.assert_called_once_with(expected_dst)

        assert (tmp_path / "dest").is_dir()

        cache.destroy()
        assert not tmp_path.exists()


class TestURLFetchStrategy:
    @pytest.fixture
    def mock_curl(self, monkeypatch):
        """Mock the curl executable."""
        mock_curl_exe = mock.MagicMock()

        def mock_which(name, required=False):
            if name == "curl":
                return mock_curl_exe
            return mock.MagicMock()

        monkeypatch.setattr(fetch_strategy, "which", mock.MagicMock(side_effect=mock_which))
        return mock_curl_exe

    @pytest.fixture
    def mock_config(self, monkeypatch):
        """Mock ramble.config."""
        config = {
            "config:url_fetch_method": "curl",
            "config:verify_ssl": True,
            "config:connect_timeout": 10,
            "config:debug": False,
        }

        def get(key, default=None):
            return config.get(key, default)

        mock_config_get = mock.MagicMock(side_effect=get)
        monkeypatch.setattr(fetch_strategy.ramble.config, "get", mock_config_get)
        return mock_config_get, config

    @pytest.fixture
    def mock_tty(self, monkeypatch):
        """Mock tty."""
        mock_msg_enabled = mock.MagicMock(return_value=False)
        monkeypatch.setattr(fetch_strategy.tty, "msg_enabled", mock_msg_enabled)
        return mock_msg_enabled

    @pytest.fixture
    def fetcher(self, tmp_path):
        """Create a URLFetchStrategy with a mock stage."""
        f = fetch_strategy.URLFetchStrategy(url="http://example.com/foo.tar.gz")

        stage = mock.MagicMock()
        stage.path = str(tmp_path)
        stage.save_filename = str(tmp_path / "foo.tar.gz")

        f.stage = stage
        return f

    def test_fetch_curl_success(self, fetcher, mock_curl, mock_config, mock_tty, tmp_path):
        """Test successful fetch with curl."""
        mock_curl.return_value = "HTTP/1.1 200 OK\r\nContent-Type: application/x-gzip"
        mock_curl.returncode = 0

        partial, save = fetcher._fetch_curl("http://example.com/foo.tar.gz")

        assert save == str(tmp_path / "foo.tar.gz")
        assert partial == str(tmp_path / "foo.tar.gz.part")

        mock_curl.assert_called_once()
        args, _ = mock_curl.call_args

        assert "http://example.com/foo.tar.gz" in args
        assert "-o" in args
        assert str(tmp_path / "foo.tar.gz.part") in args

    def test_fetch_curl_404(self, fetcher, mock_curl, mock_config, mock_tty, tmp_path):
        """Test fetch with curl when a 404 error occurs."""
        mock_curl.returncode = 22  # Not found
        fetcher.stage.archive_file = None

        partial_file = tmp_path / "foo.tar.gz.part"
        partial_file.touch()

        with pytest.raises(FailedDownloadError, match="URL .* was not found!"):
            fetcher._fetch_curl("http://example.com/foo.tar.gz")

        assert not partial_file.exists()

    def test_fetch_curl_cert_error(self, fetcher, mock_curl, mock_config, mock_tty):
        """Test fetch with curl when a certificate error occurs."""
        mock_curl.returncode = 60  # Certificate error
        fetcher.stage.archive_file = None

        with pytest.raises(FailedDownloadError, match="invalid certificate"):
            fetcher._fetch_curl("http://example.com/foo.tar.gz")

    def test_fetch_curl_content_mismatch(
        self,
        fetcher,
        mock_curl,
        mock_config,
        mock_tty,
        monkeypatch,
    ):
        """Test fetch with curl when content type is HTML."""
        mock_warn = mock.MagicMock()
        monkeypatch.setattr(fetch_strategy, "warn_content_type_mismatch", mock_warn)

        mock_curl.return_value = "HTTP/1.1 200 OK\r\nContent-Type: text/html"
        mock_curl.returncode = 0

        fetcher._fetch_curl("http://example.com/foo.tar.gz")

        mock_warn.assert_called_once()

    def test_fetch_curl_no_verify_ssl(self, fetcher, mock_curl, mock_config, mock_tty):
        """Test that -k is passed to curl when verify_ssl is false."""
        mock_config_get, config = mock_config
        config["config:verify_ssl"] = False

        mock_curl.return_value = "HTTP/1.1 200 OK"
        mock_curl.returncode = 0
        fetcher._fetch_curl("http://example.com/foo.tar.gz")

        mock_curl.assert_called_once()
        args, kwargs = mock_curl.call_args
        assert "-k" in args


class TestGitFetchStrategy:
    @pytest.fixture
    def mock_git(self, monkeypatch):
        """Mock the git executable and related functions."""
        mock_git_exe = mock.MagicMock()
        mock_git_exe.add_default_arg = mock.Mock()
        mock_git_exe.add_default_env = mock.Mock()

        def mock_which(name, required=False):
            if name == "git":
                return mock_git_exe
            return mock.MagicMock()

        monkeypatch.setattr(fetch_strategy, "which", mock.MagicMock(side_effect=mock_which))

        def mock_get_single_file(path):
            # Create a dummy directory to be "moved"
            repo_dir = os.path.join(path, "repo-dir")
            os.mkdir(repo_dir)
            return "repo-dir"

        monkeypatch.setattr(
            fetch_strategy, "get_single_file", mock.MagicMock(side_effect=mock_get_single_file)
        )
        monkeypatch.setattr(fetch_strategy.shutil, "move", shutil.move)

        return mock_git_exe

    @pytest.fixture
    def mock_config(self, monkeypatch):
        """Mock ramble.config."""
        config = {"config:debug": False, "config:verify_ssl": True}

        def get(key, default=None):
            return config.get(key, default)

        mock_config_get = mock.MagicMock(side_effect=get)
        monkeypatch.setattr(fetch_strategy.ramble.config, "get", mock_config_get)
        return mock_config_get, config

    @pytest.fixture
    def fetcher(self, tmp_path, monkeypatch):
        """Create a GitFetchStrategy with a mock stage."""
        monkeypatch.setattr(
            fetch_strategy.GitFetchStrategy,
            "version_from_git",
            mock.MagicMock(return_value=fetch_strategy.ver("2.51.0")),
        )

        f = fetch_strategy.GitFetchStrategy(git="https://example.com/repo.git")

        stage = mock.MagicMock()
        stage.path = str(tmp_path)
        stage.source_path = str(tmp_path / "source")
        f.stage = stage

        return f

    def test_clone_basic(self, fetcher, mock_git, mock_config):
        """Test basic git clone."""
        fetcher.clone()

        clone_call = None
        for call in mock_git.call_args_list:
            if "clone" in call.args:
                clone_call = call
                break

        assert clone_call is not None
        assert "https://example.com/repo.git" in clone_call.args

        assert os.path.isdir(fetcher.stage.source_path)

    def test_clone_with_commit(self, fetcher, mock_git, mock_config):
        """Test clone with a specific commit."""
        fetcher.commit = "abcdef"
        fetcher.clone(commit="abcdef")

        calls = mock_git.call_args_list

        assert "clone" in calls[0].args
        assert "https://example.com/repo.git" in calls[0].args

        assert "checkout" in calls[1].args
        assert "abcdef" in calls[1].args

        assert os.path.isdir(fetcher.stage.source_path)

    def test_clone_with_submodules(self, fetcher, mock_git, mock_config):
        """Test clone with submodules."""
        fetcher.submodules = True
        fetcher.clone()

        submodule_call = None
        for call in mock_git.call_args_list:
            if "submodule" in call.args:
                submodule_call = call
                break

        assert submodule_call is not None
        assert "update" in submodule_call.args
        assert "--init" in submodule_call.args
        assert "--recursive" in submodule_call.args

        assert os.path.isdir(fetcher.stage.source_path)
