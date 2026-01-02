# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.util import format


@pytest.mark.parametrize(
    "doc_str, kwargs, expected",
    [
        ("", {}, ""),
        (None, {}, ""),
        (
            "This is a short docstring.",
            {"indent": 4},
            "    This is a short docstring.\n",
        ),
        (
            "This  is   a\tdocstring\nwith    extra whitespace.",
            {},
            "This is a docstring with extra whitespace.\n",
        ),
        (
            "This is a very long docstring that should definitely be wrapped "
            "because it exceeds the seventy-two character limit for a single line.",
            {"indent": 2},
            "  This is a very long docstring that should definitely be wrapped because\n"
            "  it exceeds the seventy-two character limit for a single line.\n",
        ),
    ],
)
def test_format_doc(doc_str, kwargs, expected):
    """Test the format_doc function with various inputs."""
    assert format.format_doc(doc_str, **kwargs) == expected
