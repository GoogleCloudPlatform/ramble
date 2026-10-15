# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.base_app.builtin.mock.versions import Versions as VersionsBase


class VersionsStrictDisabled(VersionsBase):
    """An application with strict versioning disabled."""

    strict_versions(False)

    version("1.0", "Initial version")

    executable("test_exec", "echo '{test_variable}'")
    workload("test_wl", executable="test_exec")
