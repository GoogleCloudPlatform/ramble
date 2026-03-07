# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.util.foms import get_literal_from_regex


@pytest.mark.parametrize(
    "regex_str, expected",
    [
        (r"foo bar", "foo bar"),
        (r"Sleep for (?P<time>[0-9]+) seconds", "Sleep for"),
        (r".*?(?P<mins>[0-9]+):(?P<secs>[0-9]+)\.(?P<millisecs>[0-9]+) elapsed", ":"),
        (r"a|b", ""),
        (r"(ab|c)def", "def"),
        (r"def(a|b)c", "def"),
        (r"ab?c", "a"),
        (r"a*bc", "bc"),
        (r"a+b?c", "c"),
        (r"(optional)? required", "required"),
        (r"a(?:bc)?d", "a"),
        (r".*", ""),
        (r"^[0-9]+$", ""),
        (r"^\s*$", ""),
        (r"hello\sworld", "hello"),
        # Invalid regex
        (r"hello(w", ""),
    ],
)
def test_get_literal_from_regex_functionality(regex_str, expected):
    """Test functionality of get_literal_from_regex helper logic"""
    assert get_literal_from_regex(regex_str) == expected


def test_get_literal_from_regex_missing_sre_parse(monkeypatch):
    """Test fallback logic when sre_parse is unavailable."""
    import ramble.util.foms

    monkeypatch.setattr(ramble.util.foms, "sre_parse", None)

    assert get_literal_from_regex(r"Sleep for (?P<time>[0-9]+) seconds") == ""
