# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class ExpandedFoms(ExecutableApplication):
    name = "expanded-Foms"

    executable('foo', template=['bar', 'echo "{my_var}"'], use_mpi=False)

    input_file('input', url='file:///tmp/test_file.log',
               description='Not a file', extension='.log')

    workload('test_wl', executables=['foo'], input='input')

    workload_variable('my_var', default='1.0',
                      description='Example var',
                      workload='test_wl')

    archive_pattern('{experiment_run_dir}/archive_test.*')

    figure_of_merit('test_fom {var}',
                    fom_regex=r'Collect FOM (?P<var>\w+)\s=\s(?P<test>[0-9]+\.[0-9]+) seconds',
                    log_file='{log_file}',
                    group_name='test', units='s')

    success_criteria('Run', mode='string',
                     match=r'Collect', file='{log_file}')
