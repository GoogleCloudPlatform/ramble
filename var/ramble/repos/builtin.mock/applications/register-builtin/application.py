# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class RegisterBuiltin(ExecutableApplication):
    name = "register-builtin"

    executable("foo", "bar", use_mpi=False)
    executable("bar", "baz", use_mpi=True)
    executable("baz", "foo", use_mpi=True)

    input_file(
        "input",
        url="file:///tmp/test_file.log",
        description="Not a file",
        extension=".log",
    )

    workload("test_wl", executables=["foo"], input="input")
    workload("test_wl2", executables=["bar"], input="input")
    workload("test_wl3", executables=["baz"], input="input")

    workload_variable(
        "my_var", default="1.0", description="Example var", workload="test_wl"
    )

    archive_pattern("{experiment_run_dir}/archive_test.*")

    figure_of_merit(
        "test_fom",
        fom_regex=r"(?P<test>[0-9]+\.[0-9]+).*seconds.*",
        group_name="test",
        units="s",
    )

    # Test disabling the typically included env_vars builtin.
    register_builtin("env_vars", required=False)
    register_builtin("test_builtin", required=True)
    register_builtin("test_builtin_pre", dependents=["test_builtin"])

    def test_builtin(self):
        return ['echo "foo"']

    def test_builtin_pre(self):
        return ['echo "bar"']
