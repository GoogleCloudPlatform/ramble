# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class ObjectConflicts(ExecutableApplication):
    name = "object-conflicts"

    executable("echo", "echo", use_mpi=False)
    workload("test_wl", executable="echo")

    variant(
        "bad_spec",
        default=False,
        values=[True, False],
        description="Trigger bad conflict_spec",
    )
    variant(
        "bad_when",
        default=False,
        values=[True, False],
        description="Trigger bad when",
    )
    variant(
        "nomsg",
        default=False,
        values=[True, False],
        description="Trigger conflict with no msg",
    )

    with when("+bad_spec"):
        conflict("1 is 1")

    with when("+bad_when"):
        conflict("+bad_when", when="1 is 1")

    with when("+nomsg"):
        conflict("+nomsg")
