# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.pkgmankit import *  # noqa: F403


class Stub(PackageManagerBase):
    """Stub package manager

    This represents a package manager that does nothing. It is primarily
    provided as a mechanism to allow experiments to avoid defining required
    paths and packages.
    """

    name = "stub"

    _spec_prefix = "stub"
