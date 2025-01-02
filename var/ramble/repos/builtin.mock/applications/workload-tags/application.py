# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class WorkloadTags(ExecutableApplication):
    name = "workload-tags"

    executable("foo", 'echo "bar"', use_mpi=False)
    executable("bar", 'echo "baz"', use_mpi=False)

    workload("test_wl", executable="foo", tags=["wl-tag1", "wl-shared-tag"])
    workload("test_wl2", executable="bar", tags=["wl-tag2", "wl-shared-tag"])
