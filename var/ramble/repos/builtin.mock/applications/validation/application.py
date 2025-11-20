# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Validation(ExecutableApplication):
    name = "validation"

    executable("foo", "bar")

    workload("test_validation", executable="foo")
    workload("test_validation_workload_var", executable="foo")
    workload(
        "test_validation_workload_var_with_workload_defaults", executable="foo"
    )
    workload(
        "test_validation_workload_var_with_workload_group", executable="foo"
    )

    workload_variable(
        "validate_var",
        default="valid",
        description="A var",
        workload="test_validation",
    )

    workload_variable(
        "multi_choice_var",
        default="choice1",
        description="A variable that can only be set to values from a predefined list",
        values=["choice1", "choice2", "choice3"],
        strict=True,
        workload="test_validation_workload_var",
    )

    workload_variable(
        "multi_choice_var2",
        workload_defaults={
            "test_validation": "choice1",
            "test_validation_workload_var": "choice2",
            "test_validation_workload_var_with_workload_defaults": "choice3",
            "test_validation_workload_var_with_workload_group": "choice3",
        },
        description="A variable that can only be set to values from a predefined list",
        values=["choice1", "choice2", "choice3"],
        strict=True,
    )

    workload_group(
        "target_workloads",
        workloads=["test_validation_workload_var_with_workload_group"],
    )

    workload_variable(
        "multi_choice_var3",
        default="choice1",
        description="A variable that can only be set to values from a predefined list",
        values=["choice1", "choice2", "choice3"],
        strict=True,
        workload_group="target_workloads",
    )

    register_validator(
        name="even_processes",
        predicate="{n_nodes} * {processes_per_node} % 2 == 0",
        message="The experiment should run with even number of processes",
    )

    # A validator that only issues a warning on violation
    register_validator(
        name="validate_var_check",
        predicate='re_search(r"^valid", {validate_var})',
        message="The validate_var is recommended to start with 'valid', but got '{validate_var}'",
        fail_on_invalid=False,
    )

    # A validator with undefined vars.
    # Checking it proceeds with the validation despite the passthrough exception.
    register_validator(
        name="validate_undefined_var_check",
        predicate="{undefined_var} == 1",
        message="This validator would never be valid",
        fail_on_invalid=False,
    )
