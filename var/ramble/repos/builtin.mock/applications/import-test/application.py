# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.app.builtin.mock.import_test import helpers
from ramble.appkit import *


class ImportTest(ExecutableApplication):
    """An example application that imports a module"""

    name = "import-test"

    tags("test-app")

    executable(
        "test",
        helpers.get_test_executable(),
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    workload("test", executable="test")
