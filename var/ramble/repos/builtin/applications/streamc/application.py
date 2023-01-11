# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Streamc(SpackApplication):
    '''Define STREAMC application'''
    name = 'streamc'

    tags = ['memorybenchmark', 'microbenchmark', 'memory-benchmark', 'micro-benchmark']

    default_compiler('gcc12', base='gcc', version='12.2.0')

    software_spec('streamc',
                  base='stream',
                  version='5.10',
                  compiler='gcc12',
                  variants='+openmp cflags="-O3 -DSTREAM_ARRAY_SIZE=80000000 -DNTIMES=20"',
                  required=True)

    executable('execute_c', 'stream_c.exe')

    workload('streamc', executable='execute_c')

    log_file = '{experiment_run_dir}/{experiment_name}.out'

    figure_of_merit("Array size",
                    log_file=log_file,
                    fom_regex=r'Array size\s+\=\s+(?P<array_size>[0-9]+)',
                    group_name='array_size',
                    units='elements')

    figure_of_merit("Array memory",
                    log_file=log_file,
                    fom_regex=r'Memory per array\s+\=\s+(?P<array_mem>[0-9]+)\.*[0-9]*',
                    group_name='array_mem',
                    units='MiB')

    figure_of_merit("Total memory",
                    log_file=log_file,
                    fom_regex=r'Total memory required\s+\=\s+(?P<total_mem>[0-9]+\.*[0-9]*)',
                    group_name='total_mem',
                    units='MiB')

    figure_of_merit("Number of iterations per thread",
                    log_file=log_file,
                    fom_regex=r'Each kernel will be executed\s+(?P<n_times>[0-9]+)',
                    group_name='n_times',
                    units='')

    figure_of_merit("Number of threads",
                    log_file=log_file,
                    fom_regex=r'Number of Threads counted\s+\=\s+(?P<n_threads>[0-9]+\.*[0-9]*)',
                    group_name='n_threads',
                    units='')

    for opName in ['Copy', 'Scale', 'Add', 'Triad']:

        opname = opName.lower()

        opregex = (r'^' + opName + r':' +
                   r'\s+(?P<' + opname + r'_top_rate>[0-9]+\.[0-9]*)' +
                   r'\s+(?P<' + opname + r'_avg_time>[0-9]+\.[0-9]*)' +
                   r'\s+(?P<' + opname + r'_min_time>[0-9]+\.[0-9]*)' +
                   r'\s+(?P<' + opname + r'_max_time>[0-9]+\.[0-9]*)')

        figure_of_merit(opName + ' top rate',
                        log_file=log_file,
                        fom_regex=opregex,
                        group_name=(opname + '_top_rate'),
                        units='MB/s')

        figure_of_merit(opName + ' average time',
                        log_file=log_file,
                        fom_regex=opregex,
                        group_name=(opname + '_avg_time'),
                        units='s')

        figure_of_merit(opName + ' min time',
                        log_file=log_file,
                        fom_regex=opregex,
                        group_name=(opname + '_min_time'),
                        units='s')

        figure_of_merit(opName + ' max time',
                        log_file=log_file,
                        fom_regex=opregex,
                        group_name=(opname + '_max_time'),
                        units='s')
