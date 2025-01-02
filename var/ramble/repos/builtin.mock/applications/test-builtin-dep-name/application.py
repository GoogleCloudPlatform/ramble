# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class TestBuiltinDepName(ExecutableApplication):
    """This is an example application that will simply run the hostname command"""

    name = "test-builtin-dep-name"

    tags("test-app")

    executable(
        "standard",
        "echo test-builtin-dep-name",
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    workload("standard", executable="standard")

    # Purposely register a builtin whose leaf name collides with a builtin from pip package manager
    register_builtin("spack_activate")

    register_builtin(
        "good_pkgman_dep_name",
        required=True,
        depends_on=["package_manager_builtin::spack::spack_activate"],
    )
    register_builtin(
        "ambiguous_dep_name", required=True, depends_on=["spack_activate"]
    )

    def spack_activate(self):
        return _echo("spack_activate")

    def ambiguous_dep_name(self):
        return _echo("ambiguous_dep_name")

    def good_pkgman_dep_name(self):
        return _echo("good_pkgman_dep_name")


def _echo(text):
    return [f"echo {text}"]
