# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

class SuccessCriteriaConflictsParent(ExecutableApplication):
    name = "success-criteria-conflicts-parent"

    executable("inheritance", "echo 'PARENT'", use_mpi=False)

    workload("inheritance_wl", executable="inheritance")

    # This will fail if inheritance precedence isn't working
    with when("workload_name=inheritance_wl"):
        success_criteria(
            "test_inheritance",
            mode="string",
            anti_match="PARENT",
        )

class SuccessCriteriaConflicts(SuccessCriteriaConflictsParent):
    name = "success-criteria-conflicts"

    version("1.0.0")
    version("2.0.0")

    executable("version", "echo '{application_version}'", use_mpi=False)
    executable("success_str", "echo 'SUCCESS'", use_mpi=False)

    workload("version_wl", executable="version")
    workload("success_str_wl", executable="success_str")

    variant(
        "force_pass",
        default=False,
        values=[True, False],
    )

    # This is meant to always fail
    with when("workload_name=success_str_wl"):
        success_criteria(
            "test_success",
            mode="string",
            anti_match="SUCCESS",
        )
        with when("+force_pass"):
            success_criteria(
                "test_success",
                mode="string",
                match="SUCCESS",
            )

    with when("@1.0.0"):
        success_criteria(
            "test_version",
            mode="string",
            match="1.0.0",
        )

    with when("@2.0.0"):
        success_criteria(
            "test_version",
            mode="string",
            match="2.0.0",
        )

    # This should override the parent definition causing it to pass instead of fail
    with when("workload_name=inheritance_wl"):
        success_criteria(
            "test_inheritance",
            mode="string",
            match="PARENT",
        )
