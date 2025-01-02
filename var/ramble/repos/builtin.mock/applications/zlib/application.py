# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Zlib(ExecutableApplication):
    name = "zlib"

    software_spec("zlib", pkg_spec="zlib", package_manager="spack*")

    executable("list_lib", "ls {zlib_path}/lib", use_mpi=False)

    workload("ensure_installed", executable="list_lib")

    figure_of_merit(
        "zlib_installed",
        fom_regex=r"(?P<lib_name>libz.so.*)",
        group_name="lib_name",
        units="",
    )

    success_criteria(
        "zlib_installed", mode="string", match=r"libz.so", file="{log_file}"
    )
