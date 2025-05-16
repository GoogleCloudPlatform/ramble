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
            "echo 'Standard was {standard_variable}'",
            "echo 'PM test: {pm_var_test}'",
            "echo 'WM test: {wm_var_test}'",
            "echo 'MOD test: {mod_var_test}'",
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

    variant(
        "validation",
        default=False,
        values=[True, False],
        description="Variant to control whether validation is on or not",
    )

    with when("+validation"):
        register_validator(
            "fixed_n_nodes",
            predicate="{n_nodes} == 2",
            message="When validation is enabled, this test needs n_nodes=2",
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

            variable(
                "standard_variable",
                default="preferred",
                description="Test usage of the `variable` directive",
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

            variable(
                "standard_variable",
                default="testing",
                description="Test usage of the `variable` directive",
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

            variable(
                "standard_variable",
                default="modifier",
                description="Test usage of the `variable` directive",
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

        variable(
            "standard_variable",
            default="unincluded",
            description="Test usage of the `variable` directive",
        )
