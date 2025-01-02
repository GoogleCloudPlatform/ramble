# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

from ramble.app.builtin.mock.workload_groups import WorkloadGroups


class WorkloadGroupsInherited(WorkloadGroups):
    name = "workload-groups-inherited"

    workload("test_wl3", executable="baz")

    # Test populated group applies existing vars to new workload
    workload_group("test_wlg", workloads=["test_wl3"], mode="append")
