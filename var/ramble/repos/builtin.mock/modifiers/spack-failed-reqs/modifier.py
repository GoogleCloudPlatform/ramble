# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


class SpackFailedReqs(SpackModifier):
    """Define spack modifier requirements that will fail"""
    name = "spack-mod"

    tags('test')

    mode('default', description='This is the default mode for the spack-failed-reqs modifier')

    define_compiler('mod_compiler',
                    spack_spec='mod_compiler@1.1 target=x86_64',
                    compiler_spec='mod_compiler@1.1')

    software_spec('mod_package1',
                  spack_spec='mod_package1@1.1',
                  compiler='mod_compiler')

    software_spec('mod_package2',
                  spack_spec='mod_package2@1.1',
                  compiler='mod_compiler')

    package_manager_requirement('list not-a-package', validation_type='not_empty', modes=['default'])
