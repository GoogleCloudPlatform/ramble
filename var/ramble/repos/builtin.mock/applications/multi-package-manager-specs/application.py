# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.appkit import *


class MultiPackageManagerSpecs(ExecutableApplication):
    name = "multi-package-manager-specs"

    executable("list_env", "ls {env_path}", use_mpi=False)

    workload("check_environments", executables=["list_env"])

    with when("package_manager_family=spack"):
        software_spec("zlib", pkg_spec="zlib")

        figure_of_merit(
            "zlib_configured",
            fom_regex=r".*(?P<pkg_name>zlib\S*)",
            group_name="pkg_name",
            units="",
            log_file="{env_path}" + os.sep + "spack.yaml",
        )

        success_criteria(
            "zlib_configured",
            mode="string",
            match=r".*- zlib",
            file="{env_path}" + os.sep + "spack.yaml",
        )

    with when("package_manager_family=pip"):
        software_spec("requests", pkg_spec="requests>=2.31.0")

        figure_of_merit(
            "requests_configured",
            fom_regex=r".*(?P<pkg_name>requests\S*)",
            group_name="pkg_name",
            units="",
            log_file="{env_path}" + os.sep + "requirements.txt",
        )

        success_criteria(
            "requests_configured",
            mode="string",
            match=r".*requests",
            file="{env_path}" + os.sep + "requirements.txt",
        )
