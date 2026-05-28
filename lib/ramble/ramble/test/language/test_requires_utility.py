# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.language.shared_language
from ramble.language.language_base import DirectiveMeta


class MockObject(metaclass=DirectiveMeta):
    __module__ = "ramble.app.mock"
    required_utilities: dict = {}

    ramble.language.shared_language.requires_utility(
        name="my_ext_dep",
        git="https://github.com/my/ext_dep.git",
        commit="v1.0",
        when="@mock_when",
    )


def test_requires_utility_directive_parsing():
    obj = MockObject()
    when_list = ["@mock_when"]
    when_key = frozenset(when_list)
    assert hasattr(obj, "required_utilities")
    assert when_key in obj.required_utilities

    ext_dep = obj.required_utilities[when_key]["my_ext_dep"]
    assert ext_dep["git"] == "https://github.com/my/ext_dep.git"
    assert ext_dep["commit"] == "v1.0"
    assert ext_dep["when"] == when_list
