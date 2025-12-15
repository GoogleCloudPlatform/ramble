# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.repository
from ramble.util import object_utils


@pytest.mark.parametrize(
    "patterns,search_description,expected",
    [
        (
            ["basic*", "-test"],
            False,
            [
                "basic",
                "basic-inherited",
                "basic-inherited-nolicense",
                "basic_underscores",
                "cleanup-test",
                "import-test",
                "input-test",
            ],
        ),
        (["Mock application"], True, ["info"]),
        (["non-existent"], True, []),
    ],
)
def test_filter_by_name(
    mutable_mock_apps_repo, mutable_mock_base_apps_repo, patterns, search_description, expected
):
    assert (
        object_utils.filter_by_name(
            patterns, search_description, ramble.repository.ObjectTypes.applications
        )
        == expected
    )
