# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class SpackMod(BasicModifier):
    """Define spack modifier with various software aspects"""

    name = "spack-mod"

    tags("test")

    mode("default", description="This is the default mode for the spack-mod")

    variant(
        "missing_compiler",
        description="This variant enables software specs that refer to undefined compilers",
        default=False,
        values=[True, False],
    )

    variant(
        "implicit_compiler",
        description="This variant enables a software spec that uses an implicit compiler",
        default=False,
        values=[True, False],
    )

    variant(
        "injected_compiler",
        description="This variant enables a compiler spec that needs to be injected",
        default=False,
        values=[True, False],
    )

    with when("package_manager_family=spack"):
        package_manager_config("enable_debug", "config:debug:true")

        define_compiler(
            "mod_compiler",
            pkg_spec="mod_compiler@1.1 target=x86_64",
            compiler_spec="mod_compiler@1.1",
        )

        software_spec(
            "mod_package1",
            pkg_spec="mod_package1@1.1",
            compiler="mod_compiler",
        )

        software_spec(
            "mod_package2",
            pkg_spec="mod_package2@1.1",
            compiler="mod_compiler",
        )

        with when("+injected_compiler"):
            define_compiler(
                "injected_compiler",
                pkg_spec="injected_compiler@1.1",
                compiler_spec="injected_compiler@1.1",
                inject_if_missing=True,
            )

        with when("~missing_compiler"), when("+implicit_compiler"):
            software_spec(
                "missing_mod_package",
                pkg_spec="missing_package@1.1",
                compiler="mod_compiler",
                inject_if_missing=True,
            )

            # with when("~implicit_compiler"):
            #    software_spec(
            #        "missing_mod_package",
            #        pkg_spec="missing_package@1.1",
            #    )

        with when("+missing_compiler"):
            software_spec(
                "missing_mod_package",
                pkg_spec="missing_package@1.1",
                compiler="non_existent_compiler",
                inject_if_missing=True,
            )

    package_manager_requirement(
        "list not-a-package", validation_type="empty", modes=["default"]
    )
    package_manager_requirement(
        "list zlib", validation_type="not_empty", modes=["default"]
    )
    package_manager_requirement(
        "info zlib",
        validation_type="contains_regex",
        modes=["default"],
        regex=r"\s*Safe versions:\s*",
    )
    package_manager_requirement(
        "info zlib",
        validation_type="does_not_contain_regex",
        modes=["default"],
        regex=r"\s*Broken versions:\s*",
    )
