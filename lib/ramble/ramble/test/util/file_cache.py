# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import time

import pytest

from ramble.util.file_cache import CacheError, FileCache


@pytest.fixture
def cache(tmpdir):
    """Fixture for a file cache in a temporary directory."""
    return FileCache(str(tmpdir))


def test_init(tmpdir):
    """Test that the cache directory is created."""
    cache_root = os.path.join(str(tmpdir), "cache")
    assert not os.path.exists(cache_root)
    FileCache(cache_root)
    assert os.path.isdir(cache_root)


def test_destroy(cache):
    """Test that destroy removes all cache contents."""
    test_file = cache.cache_path("test_file")
    with open(test_file, "w") as f:
        f.write("test")
    test_dir = os.path.join(cache.root, "test_dir")
    os.makedirs(test_dir)

    assert os.path.exists(test_file)
    assert os.path.exists(test_dir)

    cache.destroy()

    assert not os.path.exists(test_file)
    assert not os.path.exists(test_dir)
    assert os.path.exists(cache.root)


def test_cache_path(cache):
    """Test the cache_path method."""
    assert cache.cache_path("foo") == os.path.join(cache.root, "foo")
    assert cache.cache_path("foo/bar") == os.path.join(cache.root, "foo", "bar")


def test_lock_path(cache):
    """Test the _lock_path method."""
    assert cache._lock_path("foo") == os.path.join(cache.root, ".foo.lock")
    assert cache._lock_path("foo/bar") == os.path.join(cache.root, "foo", ".bar.lock")


def test_init_entry_new(cache):
    """Test init_entry for a new cache entry."""
    assert not cache.init_entry("new_key")


def test_init_entry_existing_file(cache):
    """Test init_entry for an existing file."""
    key = "existing_key"
    path = cache.cache_path(key)
    with open(path, "w") as f:
        f.write("data")

    assert cache.init_entry(key)


def test_init_entry_hierarchical(cache):
    """Test init_entry for a hierarchical key."""
    key = "a/b/c"
    assert not cache.init_entry(key)
    # Check that parent directories were created
    assert os.path.isdir(os.path.dirname(cache.cache_path(key)))


def test_init_entry_is_dir_error(cache):
    """Test that init_entry raises an error if the path is a directory."""
    key = "dir_key"
    path = cache.cache_path(key)
    os.makedirs(path)

    with pytest.raises(CacheError, match="Cache file is not a file"):
        cache.init_entry(key)


def test_init_entry_file_no_access(cache, monkeypatch):
    key = "no_access_file"
    path = cache.cache_path(key)
    with open(path, "w") as f:
        f.write("data")

    orig_access = os.access

    def mock_access(p, mode):
        if p == path:
            return False
        return orig_access(p, mode)

    monkeypatch.setattr(os, "access", mock_access)

    with pytest.raises(CacheError, match="Cannot access cache file"):
        cache.init_entry(key)


def test_init_entry_dir_no_access(cache, monkeypatch):
    key = "a/no_access_dir_key"
    path = cache.cache_path(key)
    parent = os.path.dirname(path)
    os.makedirs(parent)

    orig_access = os.access

    def mock_access(p, mode):
        if p == parent:
            return False
        return orig_access(p, mode)

    monkeypatch.setattr(os, "access", mock_access)

    with pytest.raises(CacheError, match="Cannot access cache directory"):
        cache.init_entry(key)


def test_write_and_read_transaction(cache):
    """Test writing to and reading from the cache."""
    key = "my_data"
    content = "This is the data to be cached."

    with cache.write_transaction(key) as (orig_file, tmp_file):
        assert orig_file is None
        tmp_file.write(content)

    path = cache.cache_path(key)
    assert os.path.exists(path)
    with open(path) as f:
        assert f.read() == content

    with cache.read_transaction(key) as cache_file:
        assert cache_file.read() == content


def test_write_transaction_overwrite(cache):
    """Test overwriting an existing cache entry."""
    key = "overwrite_key"
    initial_content = "initial"
    new_content = "new"

    with cache.write_transaction(key) as (_, tmp):
        tmp.write(initial_content)

    with cache.write_transaction(key) as (orig_file, tmp_file):
        assert orig_file is not None
        assert orig_file.read() == initial_content
        tmp_file.write(new_content)

    with cache.read_transaction(key) as cache_file:
        assert cache_file.read() == new_content


def test_write_transaction_exception(cache):
    """Test that write transaction cleans up on exception."""
    key = "exception_key"
    path = cache.cache_path(key)
    tmp_path = path + ".tmp"

    with pytest.raises(ValueError, match="Test exception"):
        with cache.write_transaction(key) as (_, tmp):
            tmp.write("some data")
            raise ValueError("Test exception")

    assert not os.path.exists(path)
    assert not os.path.exists(tmp_path)


def test_mtime(cache):
    """Test the mtime method."""
    key = "mtime_key"

    assert cache.mtime(key) == 0

    with cache.write_transaction(key) as (_, tmp):
        tmp.write("content")
    time.sleep(0.01)

    mtime1 = cache.mtime(key)
    assert mtime1 > 0

    time.sleep(0.1)
    with cache.write_transaction(key) as (_, tmp):
        tmp.write("new content")

    mtime2 = cache.mtime(key)
    assert mtime2 > mtime1


def test_remove(cache):
    """Test removing a cache entry."""
    key = "remove_key"
    path = cache.cache_path(key)
    lock_path = cache._lock_path(key)

    with cache.write_transaction(key) as (_, tmp):
        tmp.write("data")

    assert os.path.exists(path)
    assert os.path.exists(lock_path)

    cache.remove(key)

    assert not os.path.exists(path)
    assert not os.path.exists(lock_path)


def test_read_non_existent(cache):
    """Test reading a non-existent key."""
    with pytest.raises(IOError), cache.read_transaction("non_existent_key"):
        pass
