# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
import warnings

import llnl.util.filesystem

warnings.warn(
    "The `llnl.util.symlink` module will be removed in Spack v1.1",
    category=UserWarning,
    stacklevel=2,
)

readlink = llnl.util.filesystem.readlink
islink = llnl.util.filesystem.islink
symlink = llnl.util.filesystem.symlink
