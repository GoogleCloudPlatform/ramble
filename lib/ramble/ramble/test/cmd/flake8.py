# Copyright 2022-2024 The Ramble Authors
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
    flake8("-U")
