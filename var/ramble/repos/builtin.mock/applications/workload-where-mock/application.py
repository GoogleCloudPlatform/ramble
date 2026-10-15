# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class WorkloadWhereMock(ExecutableApplication):
    name = "workload-where-mock"

    executable("test_exec", "echo '{test_var}'", use_mpi=False)

    workload_variable("test_var", default="foo", workloads=["*"])

    workload("always", executable="test_exec")
    workload(
        "only_when_var_is_foo",
        executable="test_exec",
        where=["'{test_var}' == 'foo'"],
    )
    workload(
        "exclude_when_var_is_bar",
        executable="test_exec",
        exclude_where=["'{test_var}' == 'bar'"],
    )
