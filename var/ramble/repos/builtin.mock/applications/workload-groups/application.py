# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class WorkloadGroups(ExecutableApplication):
    name = "workload-groups"

    executable("foo", 'echo "bar"', use_mpi=False)
    executable("bar", 'echo "baz"', use_mpi=False)

    workload("test_wl", executable="foo")
    workload("test_wl2", executable="bar")

    # Test empty group
    workload_group("empty", workloads=[])

    # Test populated group
    workload_group("test_wlg", workloads=["test_wl", "test_wl2"])

    # Test workload_variable that uses a group
    workload_variable(
        "test_var",
        default="2.0",
        description="Test workload vars and groups",
        workload_group="test_wlg",
    )

    # Test passing both groups an explicit workloads
    workload_variable(
        "test_var_mixed",
        default="3.0",
        description="Test vars for workload and groups",
        workload="test_wl",
        workload_group="test_wlg",
    )
