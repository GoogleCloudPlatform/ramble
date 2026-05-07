# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class ValueConflictImpossible(ExecutableApplication):
    name = "value-conflict-impossible"

    executable("base_exec", "echo 'base'", use_mpi=False)

    workload("wl1", executable="base_exec")

    with when("v=1"), when("+v"):
        workload_variable(
            "var1",
            default="val1",
            description="impossible var",
            workload="wl1",
        )
