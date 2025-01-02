# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.config


# A crude assertion to check there's no conflicting value.
# It supports only list and dict as containers, instead of
# the more general abstract types.
def _assert_no_conflict_recurse(a, b):
    if a is None or b is None:
        return
    if isinstance(a, dict):
        for k, v in a.items():
            _assert_no_conflict_recurse(v, b.get(k))
    elif isinstance(a, list):
        for i, v in enumerate(a):
            _assert_no_conflict_recurse(v, b[i])
    else:
        assert a == b


def test_default_configs_no_conflict(default_config):
    """Ensure the hard-coded config_defaults do not conflict with etc/defaults/config.yaml"""
    defaults_in_mem = ramble.config.config_defaults["config"]
    assert defaults_in_mem
    for k, v in defaults_in_mem.items():
        in_file_def = ramble.config.get(f"config:{k}")
        _assert_no_conflict_recurse(v, in_file_def)
