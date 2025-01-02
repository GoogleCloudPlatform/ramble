# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class SuccessFunction(ExecutableApplication):
    name = "success-function"

    executable("foo", 'echo "0.9 seconds"', use_mpi=False)

    workload("test_wl", executable="foo")

    figure_of_merit(
        "test_fom",
        fom_regex=r"(?P<test>[0-9]+\.[0-9]+).*seconds.*",
        group_name="test",
        units="s",
    )

    def evaluate_success(self):
        """Always fail, to help testing success functions"""
        return False
