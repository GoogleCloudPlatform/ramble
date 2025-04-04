# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class WhenVariants(ExecutableApplication):
    name = "when-variants"

    executable("test_exec", "echo '{test_variable}'", use_mpi=False)

    workload("test_wl", executable="test_exec")

    with default_args(workload="test_wl"):
        workload_variable(
            "test_variable",
            default="Test",
            description="Variable to print for testing",
        )

    variant(
        "zlib_type",
        default="preferred",
        values=["preferred", "testing"],
        description="Type of zlib to use",
    )

    variant(
        "inc_zlib",
        default=True,
        values=[True, False],
        description="Test boolean variant",
    )

    with when("package_manager_family=spack"):
        with when("+inc_zlib"):
            with when("zlib_type=preferred"):
                software_spec("zlib-pref", pkg_spec="zlib@1.2.12")

            with when("zlib_type=testing"):
                software_spec("zlib-test", pkg_spec="zlib@1.2.11")

            required_package("zlib")
