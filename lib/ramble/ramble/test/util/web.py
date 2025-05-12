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
