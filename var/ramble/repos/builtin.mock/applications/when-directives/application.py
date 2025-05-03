# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class WhenDirectives(ExecutableApplication):
    name = "when-directives"

    executable("test_exec", "echo '{test_variable}'", use_mpi=False)

    workload("test_wl", executable="test_exec")

    with default_args(workload="test_wl"):
        workload_variable(
            "test_variable",
            default="Test",
            description="Variable to print for testing",
        )

    variant(
        "register_phase_when",
        default=False,
        values=[True, False],
        description="Register additional phase using when",
    )

    with when("+register_phase_when"):
        register_phase(
            "test_phase",
            pipeline="setup",
            run_before=["get_inputs"],
        )

    def _test_phase(self, workspace, app_inst):
        print("Test Phase")
