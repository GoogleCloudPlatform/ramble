# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.package_manager import PackageManagerBase


class RunnerPackageManager(PackageManagerBase):
    """Specialized class for package managers that use a runner

    This class can be used to set up a package manager that will use a runner to perform actions
    """

    package_manager_class = "RunnerPackageManager"

    def __init__(self, file_path):
        super().__init__(file_path)
