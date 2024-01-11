# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.expander import Expander


class Nvbandwidth(SpackApplication):
    '''Define the nvbandwidth benchmark'''
    name = 'nvbandwidth'

    maintainers('rfbgo')

    tags('synthetic-benchmarks')

    software_spec('nvbandwidth', spack_spec='nvbandwidth')

    required_package('nvbandwidth')

    workload('all_benchmarks', executable='nvbandwidth')

    workload_variable('transfer-size', default='1m',
                      description='Transfer Size',
                      workloads=['multi-file', 'single-file'])

    executable(name='nvbandwidth', template='nvbandwidth', use_mpi=False)

    figure_of_merit('SUM {metric}',
                    fom_regex=r'SUM\s+(?P<metric>\w+)\s+(?P<value>\d+\.\d+)',
                    group_name='value',
                    units='GB/s')
