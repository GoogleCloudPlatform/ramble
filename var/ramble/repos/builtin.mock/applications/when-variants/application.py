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

    executable(
        "test_exec",
        template=[
            "echo '{test_variable}'",
            "echo '{test_formatted_exec}'",
        ],
        use_mpi=False,
    )

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
        values=["preferred", "testing", "modifier"],
        description="Type of zlib to use",
    )

    variant(
        "inc_zlib",
        default=True,
        values=[True, False],
        description="Test boolean variant",
    )

    with default_args(when=["package_manager_family=spack", "+inc_zlib"]):
        with when("zlib_type=preferred"):
            software_spec("zlib-pref", pkg_spec="zlib@1.2.12")

        with when("zlib_type=testing"):
            software_spec("zlib-test", pkg_spec="zlib@1.2.11")

        with when("zlib_type=modifier"):
            with when("modifier=test-mod"):
                software_spec("zlib-mod", pkg_spec="zlib@1.2.13")

        required_package("zlib")

    with when("+inc_zlib"):
        with when("zlib_type=preferred"):
            formatted_executable(
                "test_formatted_exec",
                prefix=" from_variant ",
                indentation=4,
                join_separator="\n",
                commands=[
                    "zlib included with type of preferred",
                ],
            )

        with when("zlib_type=testing"):
            formatted_executable(
                "test_formatted_exec",
                prefix=" from_variant ",
                indentation=4,
                join_separator="\n",
                commands=[
                    "zlib included with type of testing",
                ],
            )

        with when("zlib_type=modifier"):
            formatted_executable(
                "test_formatted_exec",
                prefix=" from_variant ",
                indentation=4,
                join_separator="\n",
                commands=[
                    "zlib included with type of modifier",
                ],
            )

    with when("~inc_zlib"):
        formatted_executable(
            "test_formatted_exec",
            prefix=" from_variant ",
            indentation=4,
            join_separator="\n",
            commands=[
                "zlib not included",
            ],
        )
