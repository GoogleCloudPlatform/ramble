# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.expander import Expander


class OsuMicroBenchmarks(SpackApplication):
    '''Define an OSU micro benchmarks application'''
    name = 'osu-micro-benchmarks'

    maintainers('rfbgo')

    tags('synthetic-benchmarks')

    define_compiler('gcc', spack_spec='gcc')
    software_spec('openmpi', spack_spec='openmpi')
    software_spec('osu-micro-benchmarks', spack_spec='osu-micro-benchmarks',
                  compiler='gcc')

    required_package('osu-micro-benchmarks')

    workload_variable('message-size', default='0:4194304',
                      description='Message size interval',
                      workloads=['osu_latency'])
    workload_variable('iterations', default='1000',
                      description='iterations per message size',
                      workloads=['osu_latency'])
    workload_variable('warmup', default='200',
                      description='warmup (non-included) iterations',
                      workloads=['osu_latency'])

    # Additional variables not yet included: --buffer-num, --validation,
    #  --validation-warmup, --validation-warmup

    pt2pt = {
        ('osu_bibw', 'Mb/s'),
        ('osu_bw', 'Mb/s'),
        ('osu_latency', 'us'),
        ('osu_latency_mp', 'us'),
        ('osu_latency_mt', 'us'),
        ('osu_mbw_mr', 'Mb/s'),
        ('osu_multi_lat', 'us'),
    }

    size_time_regex = r'(?P<msg_size>[0-9.]+)+\s+(?P<fom>[0-9.]+)'
    figure_of_merit_context('msg_size',
                            regex=size_time_regex,
                            output_format='Message Size: {msg_size}')

    log_str = Expander.expansion_str('log_file')
    for benchmark, unit in pt2pt:
        executable(name=f'execute-{benchmark}', template=benchmark, use_mpi=True,
                   redirect=log_str + f'-{benchmark}')
        workload(benchmark, executable=f'execute-{benchmark}')

        figure_of_merit(f'osu_{benchmark}',
                        log_file=log_str + f'-{benchmark}',
                        fom_regex=size_time_regex,
                        group_name='fom',
                        units=unit,
                        contexts=['msg_size'])
