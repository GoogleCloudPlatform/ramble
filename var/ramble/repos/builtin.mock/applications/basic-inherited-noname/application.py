# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

from ramble.app.builtin.mock.basic import Basic as BaseBasic


class BasicInheritedNoname(BaseBasic):
    """An app that intentionally has no name attribute, for unit-test purpose."""

    workload("test_wl_noname", executable="foo", input="inherited_input")
