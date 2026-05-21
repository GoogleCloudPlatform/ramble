# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class WhenVariants(ExecutableApplication):
    name = "when-variants"

    version("1.0", default=True)

    executable(
        "test_exec",
        template=[
            "echo '{test_variable}'",
            "echo '{test_formatted_exec}'",
            "echo 'Standard was {standard_variable}'",
            "echo 'PM test: {pm_var_test}'",
            "echo 'WM test: {wm_var_test}'",
            "echo 'MOD test: {mod_var_test}'",
            "echo 'Test when workload variable {test_when_var}'",
        ],
        use_mpi=False,
    )

    workload("test_wl", executable="test_exec")
    workload("test_unset_wl", executable="test_exec")

    version("2.0", description="Version 2.0 of when-variants")
    version("1.0", description="Version 1.0 of when-variants", preferred=True)

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

    variant(
        "indirect_variant",
        default="{variant_variable}",
        description="Variant who's value comes from a variable",
    )

    workload_variable(
        "variant_variable",
        default="test-value",
        description="Variable to control value of variant",
        workloads=["*"],
    )

    with when("+validation"):
        register_validator(
            "fixed_n_nodes",
            predicate="{n_nodes} == 2",
            message="When validation is enabled, this test needs n_nodes=2",
        )

        conflict(
            "zlib_type=preferred", msg="Validation requires non-preferred zlib"
        )
        conflict(
            "application_version@2.0:",
            msg="Validation does not support version 2.0 or higher",
        )

    with when("workload_name=test_wl"):
        variable(
            "test_when_var",
            default="is_defined",
            description="Test workload constrained variable definition",
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

    variant(
        "iterative_variant",
        default="{iterative_variant}",
        values=["value1", "value2", "value3"],
        description="Variant that controls variable definitions",
    )

    variant(
        "iterative_variant2",
        default="{iterative_variant2}",
        values=["value1", "value2", "value3"],
        description="Variant that controls variable definitions",
    )

    with when("iterative_variant=value1"):
        with when("iterative_variant2=value1"):
            variable(
                "leaf_variable", default="value1", description="Test variable"
            )
        variable(
            "iterative_variant2",
            default="sub_value1",
            description="Test variable",
        )

    with when("iterative_variant=value2"):
        with when("iterative_variant2=value2"):
            variable(
                "leaf_variable", default="value2", description="Test variable"
            )

        variable(
            "iterative_variant2",
            default="sub_value2",
            description="Test variable",
        )

    with when("iterative_variant=value3"):
        with when("iterative_variant2=value3"):
            variable(
                "leaf_variable", default="value3", description="Test variable"
            )

        variable(
            "iterative_variant2",
            default="sub_value3",
            description="Test variable",
        )

    # Variant Expansion
    variant(
        "pkg_args",
        values=[True, False],
        default=False,
        description="Use pkg_args",
    )

    with when("package_manager_family=spack"):
        with when("+pkg_args"):
            software_spec(
                "when-variants-{application::variant::bool}-{application::variant::val}",
                pkg_spec="when-variants@{application::when-variants::version} {application::variant::bool} {application::variant::val}",
            )

    variant(
        "bool",
        values=[True, False],
        default=True,
        description="Include bool in versions package spec",
    )

    variant(
        "val",
        values=["one", "two", "three"],
        default="three",
        description="Include val option in versions package spec",
    )
