# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.application import ApplicationBase


class ExecutableApplication(ApplicationBase):
    """Specialized class for applications that are pre-built binaries.

    This class can be used to set up an application that uses an executable
    which should already be on the platform.

    It currently only utilizes phases defined in the base class.
    """

    def __init__(self, file_path):
        super().__init__(file_path)
        self.application_class = "ExecutableApplication"
