# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class IntelMpiBenchmarks(SpackApplication):
    '''Intel MPI Benchmark applicaiton.

    https://www.intel.com/content/www/us/en/developer/articles/technical/intel-mpi-benchmarks.html
    https://github.com/intel/mpi-benchmarks
    https://www.intel.com/content/www/us/en/develop/documentation/imb-user-guide/top.html
    '''
    name = 'IntelMpiBenchmarks'

    tags = ['micro-benchmark', 'mpi']

    default_compiler('gcc9', base='gcc', version='9.3.0')
    mpi_library('impi2018', base='intel-mpi', version='2018.4.274')
    software_spec('imb', base='intel-mpi-benchmarks', version='2019.6',
                  compiler='gcc9', mpi='impi2018')

    executable('MPI1', 'IMB-MPI1 {benchmark} {flags}', use_mpi=True)

    workload('MPI1', executable='MPI1')

    workload_variable('benchmark', default='PingPong',
                      description='Benchmark name for IMB-MPI1',
                      workloads=['MPI1'])

    workload_variable('flags', default='',
                      description='Flags for running the IMB-MPI1 benchmark',
                      workloads=['MPI1'])

    figure_of_merit('Latency-0-Byte', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'\s+0\s+[0-9]+\s+(?P<latency>[0-9]+\.[0-9]+).*',
                    group_name='latency', units='usec')

    figure_of_merit('Bandwidth-0-Byte', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'\s+0\s+[0-9]+\s+[0-9]+\.[0-9]+\s+(?P<bandwidth>[0-9]+\.[0-9]+).*',
                    group_name='bandwidth', units='Mbytes/sec')

    max_exponent = 25
    for exp in range(0, max_exponent):
        size = 2**exp
        figure_of_merit('Latency-%s-Byte' % size, log_file='{experiment_run_dir}/{experiment_name}.out',
                        fom_regex=r'\s+%s\s+[0-9]+\s+(?P<latency>[0-9]+\.[0-9]+).*' % size,
                        group_name='latency', units='usec')

        figure_of_merit('Bandwidth-%s-Byte' % size, log_file='{experiment_run_dir}/{experiment_name}.out',
                        fom_regex=r'\s+%s\s+[0-9]+\s+[0-9]+\.[0-9]+\s+(?P<bandwidth>[0-9]+\.[0-9]+).*' % size,
                        group_name='bandwidth', units='Mbytes/sec')
