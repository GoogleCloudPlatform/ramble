# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Unmaintained1(ExecutableApplication):
    name = "unmaintained-1"

    executable('foo', 'bar', use_mpi=False)

    workload('test_wl', executable='foo',)
