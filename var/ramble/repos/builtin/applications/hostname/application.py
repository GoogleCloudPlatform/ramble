
# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *
from ramble.expander import Expander


class Hostname(ExecutableApplication):
    """This is an example application that will simply run the hostname command"""  # noqa: E501
    name = "hostname"

    tags("test-app")

    maintainers('douglasjacobsen')

    time_file = os.path.join(Expander.expansion_str('experiment_run_dir'),
                             'time_output')
    executable('local', 'hostname', use_mpi=False, output_capture=OUTPUT_CAPTURE.ALL)
    executable('serial', '/usr/bin/time hostname', use_mpi=False, output_capture=OUTPUT_CAPTURE.ALL)
    executable('parallel', '/usr/bin/time hostname', use_mpi=True, output_capture=OUTPUT_CAPTURE.ALL)

    workload('local', executable='local')
    workload('serial', executable='serial')
    workload('parallel', executable='parallel')

    figure_of_merit('user time from file', log_file=time_file,
                    fom_regex=r'(?P<user_time>[0-9]+\.[0-9]+)user.*',
                    group_name='user_time', units='s')

    figure_of_merit('user time',
                    fom_regex=r'(?P<user_time>[0-9]+\.[0-9]+)user.*',
                    group_name='user_time', units='s')

    figure_of_merit('possible hostname',
                    fom_regex=r'(?P<hostname>\S+)\s*',
                    group_name='hostname', units='')

    success_criteria('wrote_anything', mode='string', match=r'.*')
