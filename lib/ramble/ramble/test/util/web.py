# Copyright 2022-2025 The Ramble Authors
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


def test_uses_ssl():
    assert web.uses_ssl(url_util.parse("https://example.com")) is True
    assert web.uses_ssl(url_util.parse("http://example.com")) is False
    assert web.uses_ssl(url_util.parse("ftp://example.com")) is False
    assert web.uses_ssl(url_util.parse("file:///path/to/file")) is False

    assert web.uses_ssl(url_util.parse("gs://bucket/obj")) is True


def test_link_parser():
    html = """
    <html>
    <body>
    <a href="link1.html">Link 1</a>
    <a href="/link2.html">Link 2</a>
    <p>Some text</p>
    <a href="http://example.com/link3">Link 3</a>
    </body>
    </html>
    """
    parser = web.LinkParser()
    parser.feed(html)
    assert parser.links == ["link1.html", "/link2.html", "http://example.com/link3"]


def test_file_url_exists(tmpdir):
    existing_file = tmpdir.join("exists.txt")
    existing_file.write("content")
    assert web.url_exists(f"file://{str(existing_file)}")

    non_existing_file = tmpdir.join("does-not-exist.txt")
    assert not web.url_exists(f"file://{str(non_existing_file)}")


def test_http_url_exists(monkeypatch):
    def mock_urlopen_ok(*args, **kwargs):
        class MockResponse:
            @property
            def headers(self):
                return {"Content-type": "text/html"}

            def geturl(self):
                return "http://example.com/index.html"

            def read(self):
                return b"<html></html>"

        return MockResponse()

    monkeypatch.setattr(web, "_urlopen", mock_urlopen_ok)
    assert web.url_exists("http://example.com")

    def mock_urlopen_error(*args, **kwargs):
        from urllib.error import URLError

        raise URLError("Not Found")

    monkeypatch.setattr(web, "_urlopen", mock_urlopen_error)
    assert not web.url_exists("http://example.com/notfound")
