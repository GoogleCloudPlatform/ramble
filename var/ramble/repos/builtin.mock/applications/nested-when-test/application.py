# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class NestedWhenTest(ExecutableApplication):
    name = "nested-when-test"

    executable("base_exec", "echo 'base'", use_mpi=False)

    version("1.0", description="version 1.0")
    version("2.0", description="version 2.0")

    workload("wl1", executable="base_exec")

    with when("application_version@1.0:"):
        workload_variable(
            "test_var",
            default="val1",
            description="Compatible variable 1",
            workloads=["wl1"],
            when="application_version@1.0",
        )

        workload_variable(
            "test_var",
            default="val2",
            description="Compatible variable 2",
            workloads=["wl1"],
            when="application_version@2.0",
        )
