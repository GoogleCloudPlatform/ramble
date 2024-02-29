# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.expander import Expander


class Ior(SpackApplication):
    '''Define the IOR parallel IO benchmark. Also includes'''
    name = 'ior'

    maintainers('rfbgo')

    tags('synthetic-benchmarks', 'IO')

    define_compiler('gcc', spack_spec='gcc')
    software_spec('openmpi', spack_spec='openmpi')
    software_spec('ior', spack_spec='ior', compiler='gcc')

    required_package('ior')

    workload('multi-file', executable='ior')

    workload('single-file', executable='ior')

    workload_variable('transfer-size', default='1m',
                      description='Transfer Size',
                      workloads=['multi-file', 'single-file'])
    workload_variable('block-size', default='16m',
                      description='Block Size',
                      workloads=['multi-file', 'single-file'])
    workload_variable('segment-count', default='16',
                      description='Segment Count',
                      workloads=['multi-file', 'single-file'])

    workload_variable('iterations', default='1',
                      description='Segment Count',
                      workloads=['multi-file', 'single-file'])

    executable(name='ior', template='ior -t {transfer-size} -b {block-size} -s {segment-count} -i {iterations}', use_mpi=True)
    executable(name='ior-shared', template='{ior} -F', use_mpi=True)

    # FOMS
    # Match per iteration output in the format:
    # access    bw(MiB/s)  IOPS       Latency(s)  block(KiB) xfer(KiB)  open(s)    wr/rd(s)   close(s)   total(s)   iter
    # ------    ---------  ----       ----------  ---------- ---------  --------   --------   --------   --------   ----
    # write     560.70     2316.04    0.013670    16384      1024.00    0.002069   0.221067   0.693182   0.913139   0
    metrics = ['bw', 'IOPS', 'latency', 'block', 'xfer', 'open', 'wrrd', 'close', 'total', 'iter']
    units = ['MiB/s', 'count', 's', 'KiB', 'KiB', 's', 's', 's', 's', 'count']

    iter_regex = ''
    for metric in metrics[0:3]:  # iter is non-float
        iter_regex += r'\s+(?P<' + metric + r'>[0-9]+\.[0-9]+)'  # xfer => total
    iter_regex += r'\s+(?P<' + metrics[3] + r'>[0-9]+)'  # handle block

    for metric in metrics[4:-1]:  # iter is non-float
        iter_regex += r'\s+(?P<' + metric + r'>[0-9]+\.[0-9]+)'  # xfer => total
    iter_regex += r'\s+(?P<' + metrics[-1] + r'>[0-9]+)\s*$'  # handle iter

    access_regex = '(?P<access>(read|write))' + iter_regex
    figure_of_merit_context('iter', regex=access_regex,
                            output_format='{iter}')

    log_str = Expander.expansion_str('log_file')

    # Capture Per Iteration Data
    for metric, unit in zip(metrics, units):
        fom_regex = r'\w+' + iter_regex
        figure_of_merit(metric,
                        log_file=log_str,
                        fom_regex=fom_regex,
                        group_name=metric,
                        units=unit,
                        contexts=['iter'])

    # Capture Summary Data in the format:
    # Operation   Max(MiB)   Min(MiB)  Mean(MiB)     StdDev   Max(OPs)   Min(OPs)  Mean(OPs)     StdDev    Mean(s) Stonewall(s) Stonewall(MiB) Test# #Tasks tPN reps fPP reord reordoff reordrand seed segcnt   blksiz    xsize aggs(MiB)   API RefNum
    # write         612.90     560.70     596.63      14.15     612.90     560.70     596.63      14.15    0.85865         NA            NA     0      2   2   10   0     0        1         0    0     16 16777216  1048576     512.0 POSIX      0
    # Make a tuple of (name, unit, type) to make building the regex easier
    metrics = [
        # ('Operation', '', 'str'),
        ('bw_Max', 'MiB', 'float'),
        ('bw_Min', 'MiB', 'float'),
        ('bw_Mean', 'MiB', 'float'),
        ('bw_StdDev', '', 'float'),
        ('ops_Max', 'OPs', 'float'),
        ('ops_Min', 'OPs', 'float'),
        ('ops_Mean', 'OPs', 'float'),
        ('ops_StdDev', '', 'float'),
        ('time_Mean', 's', 'float'),
        ('time_Stonewall', 's', 'str'),  # Currently NA but may one day be a float?
        ('bw_Stonewall', 'MiB', 'str'),  # Currently NA but may one day be a float?
        ('Test_num', '', 'int'),
        ('num_Tasks', '', 'int'),
        ('tPN', '', 'int'),
        ('reps', '', 'int'),
        ('fPP', '', 'int'),
        ('reord', '', 'int'),
        ('reordoff', '', 'int'),
        ('reordrand', '', 'int'),
        ('seed', '', 'int'),
        ('segcnt', '', 'int'),
        ('blksiz', '', 'int'),
        ('xsize', '', 'int'),
        ('aggs', 'MiB', 'float'),
        ('API', '', 'str'),
        ('RefNum', '', 'int')
    ]

    summary_regex = '(?P<Operation>(read|write))'
    for name, unit, variant in metrics:
        if 'str' in variant:
            summary_regex += r'\s+(?P<' + name + r'>\w+)'
        elif 'int' in variant:
            summary_regex += r'\s+(?P<' + name + r'>[0-9]+)'
        elif 'float' in variant:
            summary_regex += r'\s+(?P<' + name + r'>[0-9]+\.[0-9]+)'
        else:
            tty.error("Incorrect metric for FOMs")

    figure_of_merit_context('summary', regex=summary_regex,
                            output_format='{Operation}')

    for metric, unit, _ in metrics:
        figure_of_merit(metric,
                        log_file=log_str,
                        fom_regex=summary_regex,
                        group_name=metric,
                        units=unit,
                        contexts=['summary'])
