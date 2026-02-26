# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class ConflictTest(ExecutableApplication):
    name = "conflict-test"

    executable("echo", "echo", use_mpi=False)
    workload("test_wl", executable="echo")

    with when("package_manager_family=spack"):
        software_spec("zlib", pkg_spec="zlib@1.2.11")
