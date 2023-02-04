# Copyright 2022-2023 Google LLC
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

    executable('test', 'echo "repo test"', use_mpi=False)

    cwd = os.getcwd()
    input_file('test', url=f'file://{cwd}/input.tar.gz',
               description='Test input')

    workload('test', executables=['test'], inputs=['test'])
