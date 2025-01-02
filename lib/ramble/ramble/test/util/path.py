# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the util/path functions"""

import os

import ramble.util.path

import pytest


@pytest.mark.parametrize(
    "path,expect",
    [
        ("rel/path", os.path.abspath("rel/path")),
        ("/abs/path", "/abs/path"),
        ("file:/abs/path", "file:/abs/path"),
        ("file:/abs/path/", "file:/abs/path"),
        ("gs://my-bucket", "gs://my-bucket"),
        ("gs://my-bucket/", "gs://my-bucket"),
        ("gs://my-bucket///", "gs://my-bucket"),
    ],
)
def test_normalize_path_or_url(path, expect):
    assert ramble.util.path.normalize_path_or_url(path) == expect
