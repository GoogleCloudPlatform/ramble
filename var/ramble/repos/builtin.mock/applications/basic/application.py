# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Basic(ExecutableApplication):
    name = "Basic Test Application"

    executable('foo', 'bar', use_mpi=False)
    executable('bar', 'baz', use_mpi=True)

    input_file('input', url='file:///tmp/test_file.log',
               description='Not a file')

    workload('test_wl', executable='foo', input='input')
    workload('test_wl2', executable='bar', input='input')

    workload_variable('my_var', default='1.0',
                      description='Example var',
                      workload='test_wl')

    archive_pattern('{experiment_run_dir}/archive_test.*')

    figure_of_merit('test_fom', 'log_file',
                    '(?P<test>[0-9]+\.[0-9]+).*seconds.*',
                    'test', 's')
