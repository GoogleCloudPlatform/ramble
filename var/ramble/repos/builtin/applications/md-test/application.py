# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.expander import Expander


class MdTest(SpackApplication):
    '''Define the MDTest parallel IO benchmark'''
    name = 'md-test'

    maintainers('rfbgo')

    tags('synthetic-benchmarks', 'IO')

    define_compiler('gcc', spack_spec='gcc')
    software_spec('openmpi', spack_spec='openmpi')

    # The IOR spack package also includes MDTest, but we implement it as a
    # separate application in ramble
    software_spec('ior', spack_spec='ior', compiler='gcc')

    required_package('ior')

    workload('multi-file', executable='ior')

    workload_variable('num-objects', default='1000',
                      description='Number of files and dirs to create (per rank)',
                      workloads=['multi-file'])
    workload_variable('iterations', default='10',
                      description='Number of iterations',
                      workloads=['multi-file'])
    workload_variable('additional-args', default='',
                      description='Pass additional args, such as working directiroy (-d)',
                      workloads=['multi-file'])

    executable(name='ior', template='mdtest -n {num-objects} -i {iterations} {additional-args}',
               use_mpi=True)

    operations = ['Directory creation', 'Directory stat', 'Directory removal', 'File creation',
                  'File stat', 'File read', 'File removal', 'Tree creation', 'Tree removal']

    unit = "ops/sec"

    metrics = ['max', 'min', 'mean', 'stddev']
    base_regex = ':'
    for metric in metrics:
        base_regex += r'\s+(?P<' + metric + r'>[0-9]+\.[0-9]+)'

    log_str = Expander.expansion_str('log_file')

    for op in operations:
        fom_regex = r'\s*' + op + r'\s+' + base_regex
        for metric in metrics:
            figure_of_merit(f'{op}-{metric}',
                            log_file=log_str,
                            fom_regex=fom_regex,
                            group_name=metric,
                            units=unit)
