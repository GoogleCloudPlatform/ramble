# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class FomLogPath(ExecutableApplication):
    name = "fom-log-path"

    executable(
        "write-fom", "echo 'fom: test'", redirect="log.file", use_mpi=False
    )
    executable(
        "write-log",
        "echo 'fom: test'",
        redirect="other.log.file",
        use_mpi=False,
    )

    workload("test", executables=["write-fom", "write-log"])

    figure_of_merit(
        "test_fom",
        fom_regex=r"fom: (?P<test>.*)",
        group_name="test",
        log_file="log.file",
        units="",
    )

    success_criteria(
        "found_test",
        mode="string",
        match=r"fom: test",
        file="log.file",
    )
