# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Versions(ExecutableApplication):
    name = "versions"
    version("0.8", description="Versions 0.8", preferred=False)

    executable("test_exec_base", "echo 'all your base are belong to us'")
    workload("test_wl_base", executable="test_exec_base")
