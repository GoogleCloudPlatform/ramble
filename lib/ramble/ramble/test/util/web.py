# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the util/web functions"""

import os
from io import BytesIO
from urllib.error import URLError

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


def test_list_url_file(tmpdir):
    d = tmpdir.mkdir("dir")
    f1 = d.join("file1.txt")
    f1.write("content")
    f2 = d.join("file2.txt")
    f2.write("content")
    sub = d.mkdir("subdir")
    f3 = sub.join("file3.txt")
    f3.write("content")

    # Test non-recursive
    file_list = web.list_url(f"file://{str(d)}")
    assert sorted(file_list) == ["file1.txt", "file2.txt"]

    # Test recursive
    file_list = web.list_url(f"file://{str(d)}", recursive=True)
    assert sorted(file_list) == ["file1.txt", "file2.txt", os.path.join("subdir", "file3.txt")]


class MockUrlOpenResponse:
    def __init__(self, url, content, headers):
        self._url = url
        self.content_stream = BytesIO(content)
        self.headers = headers

    def geturl(self):
        return self._url

    def read(self, *args):
        return self.content_stream.read(*args)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.parametrize(
    "pages_data, start_url, depth, expected_pages, expected_links",
    [
        (
            {
                "https://example.com/page1": {
                    "content": b'<html><body><a href="/page2">Page 2</a></body></html>'
                }
            },
            "https://example.com/page1",
            0,
            {"https://example.com/page1": '<html><body><a href="/page2">Page 2</a></body></html>'},
            {"https://example.com/page2"},
        ),
        (
            {
                "https://example.com/page1": {
                    "content": b'<html><body><a href="page2.html">Page 2</a></body></html>',
                },
                "https://example.com/page2.html": {
                    "content": b"<html><body>No links here</body></html>",
                },
            },
            "https://example.com/page1",
            1,
            {
                "https://example.com/page1": '<html><body><a href="page2.html">Page 2</a></body></html>',
                "https://example.com/page2.html": "<html><body>No links here</body></html>",
            },
            {"https://example.com/page2.html"},
        ),
        (
            {
                "https://example.com/pageA": {
                    "content": b'<html><body><a href="pageB.html">Page B</a></body></html>',
                },
                "https://example.com/pageB.html": {
                    "content": b'<html><body><a href="/pageA">Page A</a></body></html>',
                },
            },
            "https://example.com/pageA",
            2,
            {
                "https://example.com/pageA": '<html><body><a href="pageB.html">Page B</a></body></html>',
                "https://example.com/pageB.html": '<html><body><a href="/pageA">Page A</a></body></html>',
            },
            {"https://example.com/pageA", "https://example.com/pageB.html"},
        ),
    ],
)
def test_spider(monkeypatch, pages_data, start_url, depth, expected_pages, expected_links):
    """Centralize the mocked urlopen for spider tests to reduce duplication."""

    def mock_urlopen(req, *args, **kwargs):
        url = req.get_full_url()
        method = req.get_method()

        if url in pages_data:
            headers = {"Content-type": "text/html"}
            if method == "HEAD":
                return MockUrlOpenResponse(url, b"", headers)
            elif method == "GET":
                return MockUrlOpenResponse(url, pages_data[url]["content"], headers)

        raise URLError(f"URL not found: {url}")

    monkeypatch.setattr(web, "_urlopen", mock_urlopen)

    pages, links = web.spider(start_url, depth=depth)

    assert pages == expected_pages
    assert links == expected_links
