# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class ImpossibleWhen(ExecutableApplication):
    name = "impossible-when"

    executable("base_exec", "echo 'base'", use_mpi=False)
    executable("test_exec", "echo '{test_variable}'", use_mpi=False)
    executable("test_exec2", "echo 'Two'", use_mpi=False)

    workload("base_wl", executable="base_exec")

    workload("ver_wl1", executable="base_exec", when="@1.0")
    workload("ver_wl1", executable="base_exec", when="@2.0")

    variant(
        "workload_versions",
        default="ver1",
        values=["ver1", "ver2"],
        description="Register additional phase using when",
    )

    with when("workload_versions=ver1"):
        workload(
            "test_wl",
            executables=["base_exec", "test_exec"],
        )

        workload_variable(
            "test_variable",
            default="Test",
            description="Variable to print for testing",
            workload="test_wl",
        )

        workload_variable(
            "impossible_variable",
            default="Foo",
            description="This is an impossible variable definition",
            workload="test_wl",
            when="workload_versions=ver2",
        )

    workload(
        "test_wl",
        executables=["base_exec", "test_exec2"],
        when="workload_versions=ver2",
    )

    environment_variable(
        "APP_ENV_VAR2",
        value="TEST_WL2_ENV_VAR",
        description="Test app environment variable",
        workload="test_wl",
        when="workload_versions=ver2",
    )

    workload_variable(
        "test_variable",
        default="1",
        description="Variable to print for testing",
        workload="test_wl",
        when="workload_versions=ver2",
    )

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
