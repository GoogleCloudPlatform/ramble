# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the fetch_strategy functions"""
import os

import pytest

from ramble import fetch_strategy


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


def test_needs_stage_decorator():
    class DummyFetcher(fetch_strategy.FetchStrategy):
        @fetch_strategy._needs_stage
        def decorated_method(self):
            return True

    fetcher = DummyFetcher()
    with pytest.raises(fetch_strategy.NoStageError):
        fetcher.decorated_method()

    fetcher.stage = "dummy_stage"
    assert fetcher.decorated_method() is True


def test_ensure_one_stage_entry(tmpdir):
    # Test with one entry
    p = tmpdir.mkdir("sub")
    p.join("file.txt").write("content")
    entry_path = fetch_strategy._ensure_one_stage_entry(str(p))
    assert entry_path == os.path.join(str(p), "file.txt")

    # Test with no entries
    p_empty = tmpdir.mkdir("empty")
    with pytest.raises(AssertionError):
        fetch_strategy._ensure_one_stage_entry(str(p_empty))

    # Test with multiple entries
    p_multi = tmpdir.mkdir("multi")
    p_multi.join("file1.txt").write("content")
    p_multi.join("file2.txt").write("content")
    with pytest.raises(AssertionError):
        fetch_strategy._ensure_one_stage_entry(str(p_multi))


def test_fetch_strategy_base_class():
    fs = fetch_strategy.FetchStrategy()
    with pytest.raises(NotImplementedError):
        fs.source_id()
    with pytest.raises(NotImplementedError):
        fs.mirror_id()


def test_bundle_fetch_strategy():
    bfs = fetch_strategy.BundleFetchStrategy()
    assert bfs.fetch() is True
    assert bfs.cachable is False
    assert bfs.source_id() == ""
    assert bfs.mirror_id() is None


def test_from_url():
    url = "http://example.com/foo.tar.gz"
    fetcher = fetch_strategy.from_url(url)
    assert isinstance(fetcher, fetch_strategy.URLFetchStrategy)
    assert fetcher.url == url


def test_from_kwargs():
    # Test URLFetchStrategy
    kwargs = {"url": "http://example.com/foo.tar.gz", "checksum": "abc"}
    fetcher = fetch_strategy.from_kwargs(**kwargs)
    assert isinstance(fetcher, fetch_strategy.URLFetchStrategy)
    assert fetcher.url == kwargs["url"]
    assert fetcher.digest == kwargs["checksum"]

    # Test GitFetchStrategy
    kwargs = {"git": "https://github.com/user/repo.git", "tag": "v1.0"}
    fetcher = fetch_strategy.from_kwargs(**kwargs)
    assert isinstance(fetcher, fetch_strategy.GitFetchStrategy)
    assert fetcher.url == kwargs["git"]
    assert fetcher.tag == kwargs["tag"]

    # Test invalid args
    with pytest.raises(fetch_strategy.InvalidArgsError):
        fetch_strategy.from_kwargs(invalid_arg="foo")


def test_url_fetch_strategy_init():
    # Test successful init
    f = fetch_strategy.URLFetchStrategy(url="a", checksum="b")
    assert f.url == "a"
    assert f.digest == "b"

    # Test ValueError
    with pytest.raises(ValueError):
        fetch_strategy.URLFetchStrategy()


def test_url_fetch_strategy_ids():
    digest = "abcdef123456"
    f = fetch_strategy.URLFetchStrategy(url="a", checksum=digest)
    assert f.source_id() == digest
    expected_mirror_id = os.path.join("archive", digest[:2], digest)
    assert f.mirror_id() == expected_mirror_id

    f_no_digest = fetch_strategy.URLFetchStrategy(url="a")
    assert f_no_digest.source_id() is None
    assert f_no_digest.mirror_id() is None


def test_url_fetch_strategy_cachable():
    f = fetch_strategy.URLFetchStrategy(url="a", checksum="b")
    assert f.cachable is True

    f_no_digest = fetch_strategy.URLFetchStrategy(url="a")
    assert f_no_digest.cachable is False

    f_no_cache = fetch_strategy.URLFetchStrategy(url="a", checksum="b", no_cache=True)
    assert f_no_cache.cachable is False


def test_vcs_fetch_strategy_init():
    class DummyVCS(fetch_strategy.VCSFetchStrategy):
        url_attr = "dummy_url"

    # Test successful init
    f = DummyVCS(dummy_url="a")
    assert f.url == "a"

    # Test ValueError
    with pytest.raises(ValueError):
        DummyVCS()


def test_stable_target():
    # URLFetchStrategy with digest is stable
    f1 = fetch_strategy.URLFetchStrategy(url="a", checksum="b")
    assert fetch_strategy.stable_target(f1) is True

    # URLFetchStrategy without digest is not stable
    f2 = fetch_strategy.URLFetchStrategy(url="a")
    assert fetch_strategy.stable_target(f2) is False

    # Other fetchers are not stable
    class DummyVCS(fetch_strategy.VCSFetchStrategy):
        url_attr = "dummy_url"

    f3 = DummyVCS(dummy_url="a")
    assert fetch_strategy.stable_target(f3) is False


class TestFsCache:
    def test_init(self, tmpdir):
        cache_root = str(tmpdir.join("cache"))
        fs_cache = fetch_strategy.FsCache(cache_root)
        assert fs_cache.root == cache_root
        assert os.path.isabs(fs_cache.root)

    def test_destroy(self, tmpdir):
        cache_root = tmpdir.mkdir("cache")
        fs_cache = fetch_strategy.FsCache(str(cache_root))
        assert os.path.exists(fs_cache.root)
        fs_cache.destroy()
        assert not os.path.exists(fs_cache.root)

    def test_fetcher(self, tmpdir):
        cache_root = str(tmpdir.join("cache"))
        fs_cache = fetch_strategy.FsCache(cache_root)
        target_path = "my/target/path"
        digest = "mydigest"
        fetcher = fs_cache.fetcher(target_path, digest)

        assert isinstance(fetcher, fetch_strategy.CacheURLFetchStrategy)
        expected_path = os.path.join(cache_root, target_path)
        assert fetcher.url == expected_path
        assert fetcher.digest == digest

    def test_store(self, tmpdir):
        cache_root = str(tmpdir.join("cache"))
        fs_cache = fetch_strategy.FsCache(cache_root)
        relative_dest = "my/dest/file"

        class _DummyFetcher(fetch_strategy.FetchStrategy):
            def __init__(self, is_cachable):
                super().__init__()
                self._is_cachable = is_cachable
                self.archive_called_with = None

            @property
            def cachable(self):
                return self._is_cachable

            def archive(self, destination):
                self.archive_called_with = destination

            def source_id(self):
                return "dummy"

            def mirror_id(self):
                return "dummy"

        class _VerifyingCacheURLFetchStrategy(fetch_strategy.CacheURLFetchStrategy):
            def archive(self, destination):
                pytest.fail("archive() should not be called for CacheURLFetchStrategy")

        # Case 1: not cachable
        fetcher_not_cachable = _DummyFetcher(is_cachable=False)
        fs_cache.store(fetcher_not_cachable, relative_dest)
        assert fetcher_not_cachable.archive_called_with is None

        # Case 2: already cached (CacheURLFetchStrategy)
        fetcher_already_cached = _VerifyingCacheURLFetchStrategy(url="file:///foo", checksum="bar")
        fs_cache.store(fetcher_already_cached, relative_dest)

        # Case 3: cachable fetcher
        fetcher_cachable = _DummyFetcher(is_cachable=True)
        fs_cache.store(fetcher_cachable, relative_dest)

        expected_dst = os.path.join(cache_root, relative_dest)
        assert fetcher_cachable.archive_called_with == expected_dst
        assert os.path.exists(os.path.dirname(expected_dst))


class TestGitFetchStrategy:
    def test_init(self):
        g = fetch_strategy.GitFetchStrategy(git="some_url")
        assert g.url == "some_url"
        assert not g.submodules
        assert not g.get_full_repo
        assert not g.submodules_delete

        g2 = fetch_strategy.GitFetchStrategy(
            git="some_url", submodules=True, get_full_repo=True, submodules_delete=["a"]
        )
        assert g2.submodules
        assert g2.get_full_repo
        assert g2.submodules_delete == ["a"]

    def test_cachable(self):
        g = fetch_strategy.GitFetchStrategy(git="some_url")
        assert not g.cachable

        g_commit = fetch_strategy.GitFetchStrategy(git="some_url", commit="abc")
        assert g_commit.cachable

        g_tag = fetch_strategy.GitFetchStrategy(git="some_url", tag="v1.0")
        assert g_tag.cachable

        g_no_cache = fetch_strategy.GitFetchStrategy(git="some_url", commit="abc", no_cache=True)
        assert not g_no_cache.cachable

    def test_source_id(self):
        g_commit = fetch_strategy.GitFetchStrategy(git="some_url", commit="abc")
        assert g_commit.source_id() == "abc"

        g_tag = fetch_strategy.GitFetchStrategy(git="some_url", tag="v1.0")
        assert g_tag.source_id() == "v1.0"

        g_both = fetch_strategy.GitFetchStrategy(git="some_url", commit="abc", tag="v1.0")
        assert g_both.source_id() == "abc"

        g_none = fetch_strategy.GitFetchStrategy(git="some_url")
        assert g_none.source_id() is None

    def test_mirror_id(self):
        g = fetch_strategy.GitFetchStrategy(git="https://github.com/user/repo.git", commit="abc")
        # This test is sensitive to the implementation of urlparse and os.path.sep
        expected = os.path.sep.join(["git", "/user/repo.git", "abc"])
        assert g.mirror_id() == expected

        g_branch = fetch_strategy.GitFetchStrategy(
            git="https://github.com/user/repo.git", branch="develop"
        )
        expected_branch = os.path.sep.join(["git", "/user/repo.git", "develop"])
        assert g_branch.mirror_id() == expected_branch

        g_none = fetch_strategy.GitFetchStrategy(git="https://github.com/user/repo.git")
        assert g_none.mirror_id() is None

    def test_repo_info(self):
        g = fetch_strategy.GitFetchStrategy(git="some_url")
        assert g._repo_info() == "some_url"

        g_commit = fetch_strategy.GitFetchStrategy(git="some_url", commit="abc")
        assert g_commit._repo_info() == "some_url at commit abc"

        g_tag = fetch_strategy.GitFetchStrategy(git="some_url", tag="v1.0")
        assert g_tag._repo_info() == "some_url at tag v1.0"

        g_branch = fetch_strategy.GitFetchStrategy(git="some_url", branch="develop")
        assert g_branch._repo_info() == "some_url on branch develop"

    @pytest.mark.parametrize(
        "url, expected",
        [
            ("http://example.com", False),
            ("/", False),
            ("https://example.com", True),
            ("git@github.com:", True),
            ("file:///path/to/repo", True),
        ],
    )
    def test_protocol_supports_shallow_clone(self, url, expected):
        g = fetch_strategy.GitFetchStrategy(git=url)
        assert g.protocol_supports_shallow_clone() == expected

    def test_str(self):
        g = fetch_strategy.GitFetchStrategy(git="some_url", commit="abc")
        s = str(g)
        assert s == "[git] some_url at commit abc"
