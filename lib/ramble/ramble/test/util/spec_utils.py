# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.util.spec_utils import specs_conflict


def test_specs_conflict_no_conflict():
    new = {"pkg_spec": "zlib@1.2.11"}
    existing = {"pkg_spec": "zlib@1.2.11"}
    assert not specs_conflict(new, existing)


def test_specs_conflict_simple_conflict():
    new = {"pkg_spec": "zlib@1.2.11"}
    existing = {"pkg_spec": "zlib@1.2.12"}
    assert specs_conflict(new, existing)


def test_specs_conflict_with_prefix():
    new = {"pkg_spec": "zlib@1.2.11"}
    existing = {"p_pkg_spec": "zlib@1.2.12"}
    assert specs_conflict(new, existing, prefix="p_")


def test_specs_conflict_different_keys_no_conflict():
    new = {"pkg_spec": "zlib@1.2.11"}
    existing = {"other_spec": "zlib@1.2.12"}
    assert not specs_conflict(new, existing)


def test_specs_conflict_skip_when_same():
    new = {"pkg_spec": "zlib@1.2.11", "when": ["target=x86_64"]}
    existing = {"pkg_spec": "zlib@1.2.12", "when": ["target=x86_64"]}
    assert specs_conflict(new, existing, skip_conflicting_when=True)


def test_specs_conflict_skip_when_different():
    new = {"pkg_spec": "zlib@1.2.11", "when": ["target=x86_64"]}
    existing = {"pkg_spec": "zlib@1.2.12", "when": ["target=arm64"]}
    # If when clauses are different, they are considered NOT conflicting
    # because they won't be active at the same time.
    assert not specs_conflict(new, existing, skip_conflicting_when=True)


def test_specs_conflict_none_values_ignored():
    new = {"pkg_spec": None, "other": "val"}
    existing = {"pkg_spec": "something", "other": "val"}
    # pkg_spec in new is None, so it should be ignored.
    # other matches.
    assert not specs_conflict(new, existing)
