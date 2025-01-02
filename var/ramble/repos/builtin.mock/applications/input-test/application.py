# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *


class InputTest(ExecutableApplication):
    name = "input-test"

    executable("test", 'echo "repo test"', use_mpi=False)

    cwd = os.getcwd()
    input_file(
        "test-input1",
        url=f"file://{cwd}/input1.tar.gz",
        description="Test input",
    )

    input_file(
        "test-input2",
        url=f"file://{cwd}/input2.tar.gz",
        description="Test input",
    )

    input_file(
        "test-input3",
        url=f"file://{cwd}/input3.txt",
        expand=False,
        description="Test input",
    )

    workload(
        "test",
        executables=["test"],
        inputs=["test-input1", "test-input2", "test-input3"],
    )
