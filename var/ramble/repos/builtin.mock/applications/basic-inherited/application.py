# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

from ramble.app.builtin.mock.basic import Basic as BaseBasic


class BasicInherited(BaseBasic):
    name = "Basic Inheritance Test Application"

    input_file('inherited_input', url='file:///tmp/inherited_file.log',
               description='Again, not a file', extension='.log')

    workload('test_wl3', executable='foo', input='inherited_input')
