# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class VersionImpossible(ExecutableApplication):
    name = "version-impossible"

    executable("base_exec", "echo 'base'", use_mpi=False)

    workload("wl1", executable="base_exec", when="@1.0")
    workload("wl1", executable="base_exec", when="@2.0")

    workload_variable(
        "var1",
        default="val1",
        description="var for 1.0",
        workload="wl1",
        when="@1.0",
    )

    workload_variable(
        "var2",
        default="val2",
        description="var for 2.0",
        workload="wl1",
        when="@2.0",
    )
