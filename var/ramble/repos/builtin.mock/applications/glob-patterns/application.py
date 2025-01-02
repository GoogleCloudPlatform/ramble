# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class GlobPatterns(ExecutableApplication):
    name = "glob-patterns"

    executable(
        "test", "base test {test_var} {glob_var} {baz_var}", use_mpi=False
    )
    executable(
        "test-foo",
        "test foo {test_var} {glob_var} {baz_var} {mod_var}",
        use_mpi=False,
    )
    executable(
        "test-bar", "test bar {test_var} {glob_var} {baz_var}", use_mpi=True
    )
    executable("baz", "baz {test_var} {glob_var} {baz_var}", use_mpi=True)

    input_file(
        "input",
        url="file:///tmp/test_file.log",
        description="Not a file",
        extension=".log",
    )
    input_file(
        "input-foo",
        url="file:///tmp/test_foo_file.log",
        description="Not a file",
        extension=".log",
    )
    input_file(
        "input-bar",
        url="file:///tmp/test_bar_file.log",
        description="Not a file",
        extension=".log",
    )
    input_file(
        "baz",
        url="file:///tmp/baz_file.log",
        description="Not a file",
        extension=".log",
    )

    workload("test_one_exec", executables=["test"], inputs=["input"])
    workload("test_three_exec", executables=["test*"], inputs=["input*"])
    workload("one_baz_exec", executables=["baz"], inputs=["baz"])

    environment_variable(
        "env_var_test",
        "set",
        description="Test env var",
        workloads=["test_one_exec"],
    )
    environment_variable(
        "env_var_glob", "set", description="Test env var", workloads=["test*"]
    )
    environment_variable(
        "env_var_baz",
        "set",
        description="Test env var",
        workloads=["one_baz_exec"],
    )
    environment_variable(
        "env_var_mod",
        "set",
        description="Env var to be modified",
        workloads=["test_three_exec"],
    )

    workload_variable(
        "test_var",
        default="wl_var_test",
        description="Example var",
        workloads=["test_one_exec"],
    )
    workload_variable(
        "glob_var",
        default="wl_var_glob",
        description="Example var",
        workloads=["test*"],
    )
    workload_variable(
        "baz_var",
        default="wl_var_baz",
        description="Example var",
        workloads=["one_baz_exec"],
    )
    workload_variable(
        "var_mod",
        default="wl_var_mod",
        description="Variable to be modified",
        workloads=["test_three_exec"],
    )

    figure_of_merit(
        "test_fom",
        fom_regex=r"(?P<test>[0-9]+\.[0-9]+).*seconds.*",
        group_name="test",
        units="s",
    )
