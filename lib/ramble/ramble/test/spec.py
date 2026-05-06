# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.spec import Spec, SpecFormatStringError


class TestSpec:
    """Tests for the Spec class."""

    @pytest.mark.parametrize(
        "spec_str, expected_name, expected_namespace, expected_fullname",
        [
            ("my-app", "my-app", None, "my-app"),
            ("my-namespace.my-app", "my-app", "my-namespace", "my-namespace.my-app"),
            ("", "", None, ""),
        ],
    )
    def test_init_from_string(
        self, spec_str, expected_name, expected_namespace, expected_fullname
    ):
        s = Spec(spec_str)
        assert s.name == expected_name
        assert s.namespace == expected_namespace
        assert s.fullname == expected_fullname

    def test_init_empty_and_copy(self):
        # Test default constructor
        s_empty = Spec()
        assert s_empty.name is None
        assert s_empty.namespace is None
        assert s_empty.fullname == ""

        # Test init from another spec and copy method
        s1 = Spec("my-namespace.my-app")
        s2 = Spec(s1)
        s3 = s1.copy()

        for s in [s2, s3]:
            assert s.name == "my-app"
            assert s.namespace == "my-namespace"
            assert s.fullname == "my-namespace.my-app"
            assert s is not s1

    def test_format(self):
        s = Spec("ns.app")
        assert s.format("{name}") == "app"
        assert s.format("{namespace}") == "ns"
        assert s.format("{fullname}") == "ns.app"
        assert s.format("Name: {name}, Namespace: {namespace}") == "Name: app, Namespace: ns"

    @pytest.mark.parametrize("format_str", ["{", "}", "{foo", "{_private}", "{nonexistent}"])
    def test_format_errors(self, format_str):
        s = Spec("ns.app")
        with pytest.raises(SpecFormatStringError):
            s.format(format_str)
