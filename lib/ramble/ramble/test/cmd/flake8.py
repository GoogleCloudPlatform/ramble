# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import deprecation

from ramble.main import RambleCommand

flake8 = RambleCommand("flake8")


@deprecation.fail_if_not_removed
def test_flake8_deprecation():
    # Call `ramble flake8` to trigger the deprecation assertion.
    # Do not test on actual sources, since we don't actually want
    # to verify styles using this command, which may diverge from
    # `ramble style`. One such divergence is on modifiers, where
    # the style command has additional flake8 exemptions.
    flake8("-U", "/dev/null")
