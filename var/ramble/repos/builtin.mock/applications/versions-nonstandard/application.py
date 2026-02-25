# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.base_app.builtin.mock.versions import Versions as VersionsBase


class VersionsNonstandard(VersionsBase):
    name = "versions-nonstandard"

    executable("test_exec", "echo '{test_variable}'", use_mpi=False)

    workload("test_wl", executable="test_exec")
    workload_group("test_wl_group", workloads=["test_wl"])

    with default_args(workload="test_wl"):
        workload_variable(
            "test_variable",
            default="Test",
            description="Variable to print for testing",
        )

    version("1_01", description="Versions 1_01", preferred=True)
    version("1_02", description="Versions 1_02")
    version("2_0a1", description="Versions 2_0a1")
    # Version 0.8 imported from base_application.py

    @staticmethod
    def version_to_pep440(version):
        return version.replace("_", ".")

    @staticmethod
    def pep440_to_version(version):
        return version.replace(".", "_")

    with default_args(when=["package_manager_family=spack"]):

        software_spec(
            "versions-nonstandard-{application_version}",
            pkg_spec="versions-nonstandard@{application_version}",
        )

        required_package("versions-nonstandard")

        with when("application_version@1_01"):
            software_spec("zlib-exact", pkg_spec="zlib@1.2.14")
            required_package("zlib")

        with when("application_version@1_02:"):
            software_spec("zlib-greater", pkg_spec="zlib@1.2.13")
            required_package("zlib")

        with when("application_version@1_01:1_02"):
            software_spec("zlib-range", pkg_spec="zlib@1.2.12")
            required_package("zlib")

        with when("application_version@:1_01"):
            software_spec("zlib-less", pkg_spec="zlib@1.2.11")
            required_package("zlib")
