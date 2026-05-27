# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.filters
from ramble.workspace import RambleWorkspaceError


def test_translate_group_to_predicate():
    # Test empty group
    assert ramble.filters.translate_group_to_predicate({}) == "True"
    assert ramble.filters.translate_group_to_predicate(None) == "True"

    # Test only where
    group_only_where = {"where": ["{n_nodes} < 4", "{workload} == 'foo'"]}
    assert (
        ramble.filters.translate_group_to_predicate(group_only_where)
        == "(({n_nodes} < 4) and ({workload} == 'foo'))"
    )

    # Test only exclude_where
    group_only_exclude = {"exclude_where": ["{mpi} == 'tcp'", "{platform} == 'bar'"]}
    assert (
        ramble.filters.translate_group_to_predicate(group_only_exclude)
        == "(not ({mpi} == 'tcp') and not ({platform} == 'bar'))"
    )

    # Test both
    group_both = {"where": ["{n_nodes} < 4"], "exclude_where": ["{mpi} == 'tcp'"]}
    assert (
        ramble.filters.translate_group_to_predicate(group_both)
        == "(({n_nodes} < 4)) and (not ({mpi} == 'tcp'))"
    )


def test_expand_filter_groups():
    filter_groups_defs = {
        "small-scale": {"where": ["{n_nodes} < 4"]},
        "single-node": {"where": ["{n_nodes} == 1"]},
        "tcp-only": {"exclude_where": ["{mpi} != 'tcp'"]},
    }

    # Test empty expression
    assert ramble.filters.expand_filter_groups("", filter_groups_defs) == "True"
    assert ramble.filters.expand_filter_groups(None, filter_groups_defs) == "True"

    # Test single group
    assert (
        ramble.filters.expand_filter_groups("small-scale", filter_groups_defs)
        == "( (({n_nodes} < 4)) )"
    )

    # Test logical expression
    assert (
        ramble.filters.expand_filter_groups("small-scale and not single-node", filter_groups_defs)
        == "( (({n_nodes} < 4)) ) and not ( (({n_nodes} == 1)) )"
    )

    # Test parentheses
    assert (
        ramble.filters.expand_filter_groups(
            "(small-scale or tcp-only) and not single-node", filter_groups_defs
        )
        == "( ( (({n_nodes} < 4)) ) or ( (not ({mpi} != 'tcp')) ) ) and not ( (({n_nodes} == 1)) )"
    )

    # Test invalid group
    with pytest.raises(RambleWorkspaceError):
        ramble.filters.expand_filter_groups("invalid-group", filter_groups_defs)

    # Test invalid characters
    with pytest.raises(RambleWorkspaceError):
        ramble.filters.expand_filter_groups("small-scale & tcp-only", filter_groups_defs)

    # Test None defs
    assert ramble.filters.expand_filter_groups("", None) == "True"
    with pytest.raises(RambleWorkspaceError):
        ramble.filters.expand_filter_groups("small-scale", None)
