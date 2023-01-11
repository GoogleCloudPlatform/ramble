
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

    executable('serial', '/usr/bin/time hostname', use_mpi=False)
    executable('parallel', '/usr/bin/time hostname', use_mpi=True)

    workload('serial', executable='serial')
    workload('parallel', executable='parallel')

    figure_of_merit('user time', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'(?P<user_time>[0-9]+\.[0-9]+)user.*',
                    group_name='user_time', units='s')
