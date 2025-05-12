# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the fetch_strategy functions"""

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
