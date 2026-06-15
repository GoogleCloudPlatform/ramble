# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the util/web functions"""


import pytest

from ramble.util import web

from spack.util import url as url_util


def test_get_header():
    headers = {"Content-type": "text/plain"}

    assert web.get_header(headers, "Content-type") == "text/plain"

    # test fuzzy lookup
    assert web.get_header(headers, "contentType") == "text/plain"
    headers["contentType"] = "text/html"
    assert web.get_header(headers, "contentType") == "text/html"

    # test no match
    with pytest.raises(KeyError):
        web.get_header(headers, "ContentLength")


def test_gcs_url_exists(monkeypatch):

    def _get_client():
        return MockGcsClient()

    import spack.util.gcs

    monkeypatch.setattr(spack.util.gcs, "gcs_client", _get_client)
    test_url = "gs://abc/xyz.txt"
    with pytest.raises(MockGcsClientError, match="Mock error for bucket abc"):
        web.url_exists(test_url)


class MockGcsClient:
    def bucket(self, name):
        raise MockGcsClientError(f"Mock error for bucket {name}")


class MockGcsClientError(Exception):
    pass


def test_uses_ssl(monkeypatch):
    # Test https
    url = url_util.parse("https://example.com")
    assert web.uses_ssl(url)

    # Test http
    url = url_util.parse("http://example.com")
    assert not web.uses_ssl(url)

    # Test s3 without S3_ENDPOINT_URL
    url = url_util.parse("s3://my-bucket/key")
    assert web.uses_ssl(url)

    # Test s3 with http S3_ENDPOINT_URL
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://s3.local")
    url = url_util.parse("s3://my-bucket/key")
    assert not web.uses_ssl(url)

    # Test s3 with https S3_ENDPOINT_URL
    monkeypatch.setenv("S3_ENDPOINT_URL", "https://s3.local")
    url = url_util.parse("s3://my-bucket/key")
    assert web.uses_ssl(url)
    monkeypatch.delenv("S3_ENDPOINT_URL")

    # Test gs
    url = url_util.parse("gs://my-bucket/key")
    assert web.uses_ssl(url)

    # Test file
    url = url_util.parse("file:///path/to/file")
    assert not web.uses_ssl(url)


def test_url_exists_file(tmpdir):
    # Test existing file
    p = tmpdir.join("exists.txt")
    p.write("content")
    assert web.url_exists(f"file://{str(p)}")

    # Test non-existing file
    assert not web.url_exists(f"file://{str(p)}/nonexistent.txt")


def test_push_to_url_file(tmpdir):
    local_file = tmpdir.join("local.txt")
    local_file.write("some data")
    remote_dir = tmpdir.mkdir("remote")
    remote_file_path = remote_dir.join("remote.txt")

    # Test copy
    web.push_to_url(str(local_file), f"file://{str(remote_file_path)}", keep_original=True)
    assert local_file.exists()
    assert remote_file_path.exists()
    assert remote_file_path.read() == "some data"
    remote_file_path.remove()

    # Test move
    web.push_to_url(str(local_file), f"file://{str(remote_file_path)}", keep_original=False)
    assert not local_file.exists()
    assert remote_file_path.exists()
    assert remote_file_path.read() == "some data"


def test_remove_url_file(tmpdir):
    # Test remove file
    p = tmpdir.join("file.txt")
    p.write("content")
    web.remove_url(f"file://{str(p)}")
    assert not p.exists()

    # Test remove directory recursively
    d = tmpdir.mkdir("dir")
    f = d.join("file.txt")
    f.write("content")
    web.remove_url(f"file://{str(d)}", recursive=True)
    assert not d.exists()
