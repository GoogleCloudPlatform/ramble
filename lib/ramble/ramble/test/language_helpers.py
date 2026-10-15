# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest
from packaging.specifiers import SpecifierSet

from ramble.language.language_helpers import _parse_version_spec, is_specifier_set_compatible


@pytest.mark.parametrize(
    "val,expected",
    [
        ("1.0", SpecifierSet("==1.0")),
        ("1.0:", SpecifierSet(">=1.0")),
        (":2.0", SpecifierSet("<=2.0")),
        ("1.0:2.0", SpecifierSet(">=1.0,<=2.0")),
        ("1_0", SpecifierSet("==1.0")),
        ("1_0_1:", SpecifierSet(">=1.0.1")),
        (":2_0_0a1", SpecifierSet("<=2.0.0a1")),
        ("1_0:2_0", SpecifierSet(">=1.0,<=2.0")),
        ("", SpecifierSet()),
    ],
)
def test_parse_version_spec(val, expected):
    assert _parse_version_spec(val) == expected


@pytest.mark.parametrize(
    "specs,expected",
    [
        # Empty
        ([], True),
        # Single bounds
        ([">=1.0"], True),
        (["<=2.0"], True),
        (["==1.5"], True),
        # Multiple ==
        (["==1.0", "==1.0"], True),
        (["==1.0", "==2.0"], False),
        # == and ranges (compatible)
        (["==1.5", ">=1.0"], True),
        (["==1.5", "<=2.0"], True),
        (["==1.5", ">=1.0", "<=2.0"], True),
        # == and ranges (incompatible)
        (["==1.5", ">=2.0"], False),
        (["==1.5", "<=1.0"], False),
        (["==1.5", ">1.5"], False),
        (["==1.5", "<1.5"], False),
        # Ranges overlapping
        ([">=1.0", "<=2.0"], True),
        ([">=2.0", "<=2.0"], True),
        # Ranges non-overlapping
        ([">=2.0", "<=1.0"], False),
        # Exclusive boundary overlap
        ([">2.0", "<=2.0"], False),
        ([">=2.0", "<2.0"], False),
        ([">2.0", "<2.0"], False),
    ],
)
def test_is_specifier_set_compatible(specs, expected):
    spec_set = SpecifierSet()
    for s in specs:
        spec_set &= SpecifierSet(s)
    assert is_specifier_set_compatible(spec_set) is expected
