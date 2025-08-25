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

    workload_variable(
        "validate_var",
        default="valid",
        description="A var",
        workload="test_validation",
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
