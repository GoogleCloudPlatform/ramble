
# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Hostname(ExecutableApplication):
    """This is an example application that will simply run the hostname command"""  # noqa: E501
    name = "hostname"

    tags = ["test-app"]

    input_file('test', url="https://no.domain/file/test_dir.tgz", description="Example input file...")

    executable('local', 'time hostname', use_mpi=False, output_capture=OUTPUT_CAPTURE.ALL)
    executable('serial', '/usr/bin/time hostname', use_mpi=False, output_capture=OUTPUT_CAPTURE.ALL)
    executable('parallel', '/usr/bin/time hostname', use_mpi=True, output_capture=OUTPUT_CAPTURE.ALL)

    workload('local', executable='local')
    workload('serial', executable='serial')
    workload('parallel', executable='parallel')

    figure_of_merit('user time', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'(?P<user_time>[0-9]+\.[0-9]+)user.*',
                    group_name='user_time', units='s')

    success_criteria('has_user_time', mode='string', match=r'[0-9]+\.[0-9]+user.*', file='{experiment_run_dir}/{experiment_name}.out')
