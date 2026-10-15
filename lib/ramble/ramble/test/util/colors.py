# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.util.colors import auto_escape


@pytest.mark.parametrize(
    "input_str,expected",
    [
        # Literal @
        ("@@", "@@"),
        ("@@@", "@@@@"),
        # Valid color code (blue) within a string - now escaped because it looks like a version
        ("foo@bar", "foo@@bar"),
        ("email@example.com", "email@@example.com"),  # @e is not a color
        # Preceded by special chars (should NOT be escaped if valid color)
        (" (@gLinked@.)", " (@gLinked@.)"),
        # Valid color codes (should NOT be escaped)
        ("@r", "@r"),
        ("@R", "@R"),
        ("@. ", "@. "),
        ("@*r", "@*r"),
        ("@_g", "@_g"),
        ("@*K", "@*K"),
        ("@*W", "@*W"),
        ("@*", "@*"),
        ("@_", "@_"),
        # Valid color codes with braces (should NOT be escaped even if preceded by alnum)
        ("foo@r{text}", "foo@r{text}"),
        ("@{text}", "@{text}"),
        ("@r{text}", "@r{text}"),
        ("@*b{text}", "@*b{text}"),
        ("@_{text}", "@_{text}"),
        ("@*R{text}", "@*R{text}"),
        ("@*r{text}", "@*r{text}"),
        # Complex cases
        ("Error at @r{@*line 10}@. in @*file.py", "Error at @r{@*line 10}@. in @*file.py"),
        ("Multiple @@ characters", "Multiple @@ characters"),
        # Missing closing brace: @r is matched by itself
        ("Missing brace: @r{text", "Missing brace: @r{text"),
        # Versions and specs
        ("gromacs@2021", "gromacs@@2021"),
        ("package-name@version", "package-name@@version"),
        ("package_name@version", "package_name@@version"),
    ],
)
def test_auto_escape(input_str, expected):
    assert auto_escape(input_str) == expected


def test_auto_escape_unsupported_color():
    # @e is not supported.
    assert auto_escape("@e") == "@@e"
