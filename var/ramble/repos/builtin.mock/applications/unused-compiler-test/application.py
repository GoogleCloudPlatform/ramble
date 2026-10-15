# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class UnusedCompilerTest(ExecutableApplication):
    name = "unused-compiler-test"

    executable("echo", "echo", use_mpi=False)
    workload("test_wl", executable="echo")

    define_compiler("my_unused_compiler", pkg_spec="gcc@11.1.0")
