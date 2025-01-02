# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Basic(ExecutableApplication):
    name = "basic"

    executable("foo", "bar", use_mpi=False)
    executable("bar", "baz", use_mpi=True)
    executable("echo", 'echo "0.25 seconds"', use_mpi=False)

    input_file(
        "input",
        url="file:///tmp/test_file.log",
        description="Not a file",
        extension=".log",
    )

    workload("test_wl", executable="foo", input="input")
    workload("test_wl2", executable="bar", input="input")
    workload("working_wl", executable="echo")

    workload_variable(
        "my_base_var",
        default="0.0",
        description="Example var",
        workload="test_wl",
    )

    workload_variable(
        "my_var", default="1.0", description="Example var", workload="test_wl"
    )

    environment_variable(
        "TEST_ENV", value="1", description="test var", workload="test_wl"
    )

    archive_pattern("{experiment_run_dir}/archive_test.*")

    figure_of_merit(
        "test_fom",
        fom_regex=r"(?P<test>[0-9]+\.[0-9]+).*seconds.*",
        group_name="test",
        units="s",
    )
