# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.base_app.builtin.mock.versions import Versions as VersionsBase


class Versions(VersionsBase):
    name = "versions"

    executable("test_exec", "echo '{test_variable}'", use_mpi=False)

    workload("test_wl", executable="test_exec")
    workload_group("test_wl_group", workloads=["test_wl"])

    with default_args(workload="test_wl"):
        workload_variable(
            "test_variable",
            default="Test",
            description="Variable to print for testing",
        )

        environment_variable(
            "APP_ENV_VAR",
            value="APP_ENV_VAR_SET",
            description="Test app environment variable",
            workload="test_wl",
            when=["@:0.9"],
        )

    version("2.0a1", description="Versions 2.0 alpha")
    version("1.0", description="Versions 1.0", preferred=True)
    version("0.9", description="Versions 0.9")
    # Version 0.8 imported from base_application.py

    with default_args(when=["package_manager_family=spack"]):

        with when("application_version@1.0"):
            software_spec("zlib-exact", pkg_spec="zlib@1.2.14")

        with when("application_version@1.0:"):
            software_spec("zlib-greater", pkg_spec="zlib@1.2.13")

        with when("application_version@0.9:1.0"):
            software_spec("zlib-range", pkg_spec="zlib@1.2.12")

        with when("@:0.9"):
            software_spec("zlib-less", pkg_spec="zlib@1.2.11")

        required_package("zlib")
