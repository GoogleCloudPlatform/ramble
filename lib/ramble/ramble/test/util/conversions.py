# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.util import conversions


@pytest.mark.parametrize(
    "input,expect",
    [
        ("not-a-list", "not-a-list"),
        ("[1,2, 3, a, b, c]", ["1", "2", "3", "a", "b", "c"]),
    ],
)
def test_list_str_to_list(input, expect):
    assert conversions.list_str_to_list(input) == expect


@pytest.mark.parametrize(
    "input,expect",
    [
        (None, None),
        ("none", None),
        ("None", None),
        ("", None),
        ("other", "other"),
    ],
)
def test_canonical_none(input, expect):
    assert conversions.canonical_none(input) == expect


@pytest.mark.parametrize(
    "input,expect",
    [
        (None, None),
        ("foo", "foo"),
        (1, 1),
        (-1.2, -1.2),
        ("-1.2", -1.2),
        ("-10", -10),
        ("1.0", 1),
    ],
)
def test_convert_to_number(input, expect):
    assert conversions.convert_to_number(input) == expect
