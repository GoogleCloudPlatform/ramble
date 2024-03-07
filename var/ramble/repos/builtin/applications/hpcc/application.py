# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
from ramble.expander import Expander


class Hpcc(SpackApplication):
    '''Define the HPCC application

    HPCC is a collection of multiple benchmarks, which include:
      - HPL
      - DGEMM
      - STREAM
      - PTRANS
      - MPIRandomAccess
      - FFT
      - LatencyBandwidth
    '''
    name = 'hpcc'

    maintainers('rfbgo')

    tags('benchmark-app', 'mini-app', 'benchmark', 'DGEMM')

    define_compiler('gcc9', spack_spec='gcc@9.3.0')

    software_spec('impi2018',
                  spack_spec='intel-mpi@2018.4.274')

    software_spec('hpcc',
                  spack_spec='hpcc@1.5.0',
                  compiler='gcc9')

    required_package('hpcc')

    input_file('hpccinf', url='{config_file}', expand=False,
               sha256='fe9e5f4118c1b40980e162dc3c52d224fd6287e9706b95bb40ae7dfc96b38622',
               description='Input/Config file for HPCC benchmark')

    executable('copy-config', template='cp -R {workload_input_dir}/* {experiment_run_dir}/.', use_mpi=False)

    executable('execute', 'hpcc', use_mpi=True)

    workload_variable('config_file', default='https://raw.githubusercontent.com/icl-utk-edu/hpcc/1.5.0/_hpccinf.txt',
                      description='Default config file',
                      workloads=['standard'])

    workload('standard', executables=['copy-config', 'execute'], input='hpccinf')

    workload_variable('out_file', default='{experiment_run_dir}/hpccoutf.txt',
                      description='Output file for results',
                      workloads=['standard'])

    output_sections = ['HPL', 'LatencyBandwidth', 'MPIFFT', 'MPIRandomAccess_LCG',
                       'MPIRandomAccess', 'PTRANS', 'SingleDGEMM', 'SingleFFT',
                       'SingleRandomAccess_LCG', 'SingleRandomAccess', 'SingleSTREAM',
                       'StarDGEMM', 'StarFFT', 'StarRandomAccess_LCG', 'StarRandomAccess',
                       'StarSTREAM', 'Summary']

    context_regex = 'Begin of Summary section'
    figure_of_merit_context('Summary', regex=context_regex, output_format='Summary')

    summary_metrics = [
        ('HPL_Tflops', 'Tflops'),
        ('StarDGEMM_Gflops', 'Gflops'),
        ('SingleDGEMM_Gflops', 'Gflops'),
        ('PTRANS_GBs', 'GB/s'),
        ('MPIRandomAccess_GUPs', 'GUP/s'),
        ('MPIRandomAccess_LCG_GUPs', 'GUP/s'),
        ('StarRandomAccess_GUPs', 'GUP/s'),
        ('SingleRandomAccess_GUPs', 'GUP/s'),
        ('StarSTREAM_Copy', 'GB/s'),
        ('StarSTREAM_Scale', 'GB/s'),
        ('StarSTREAM_Add', 'GB/s'),
        ('StarSTREAM_Triad', 'GB/s'),
        ('SingleSTREAM_Copy', 'GB/s'),
        ('SingleSTREAM_Scale', 'GB/s'),
        ('SingleSTREAM_Add', 'GB/s'),
        ('SingleSTREAM_Triad', 'GB/s'),
        ('StarFFT_Gflops', 'Gflops'),
        ('SingleFFT_Gflops', 'Gflops'),
        ('MPIFFT_Gflops', 'Gflops'),
        ('MaxPingPongLatency_usec', 'usec'),
        ('RandomlyOrderedRingLatency_usec', 'usec'),
        ('MinPingPongBandwidth_GBytes', 'GB/s'),
        ('NaturallyOrderedRingBandwidth_GBytes', 'GB/s'),
        ('RandomlyOrderedRingBandwidth_GBytes', 'GB/s')
    ]

    log_str = Expander.expansion_str('out_file')

    for metric, unit in summary_metrics:
        summary_regex = metric + r'=(?P<val>[0-9]+\.[0-9]+)'
        figure_of_merit(metric,
                        log_file=log_str,
                        fom_regex=summary_regex,
                        group_name='val', units=unit,
                        contexts=['Summary']
                        )
    '''
    # Below is a list of the full metrics available in the output. The current
    # implementation captures the summary metrics, which is sufficient,  but it
    # is possible a feature user wants to expand the FOM capture to include the
    # metrics below. As such they are left here for completeness.
    # Full Metrics:
        #  HPL
            # T/V                N    NB     P     Q               Time                 Gflops
            #--------------------------------------------------------------------------------
            # WR11C2R4        1000    80     2     2               0.01              7.188e+01
        #  DGEMM
            # SingleDGEMM
                # Single DGEMM Gflop/s 43.075235
        # StarDGEMM
            # Minimum Gflop/s 24.895763
            # Average Gflop/s 33.317999
            # Maximum Gflop/s 37.322778
        #  STREAM
            # StarSTREAM
                # Minimum Copy GB/s 35.172220
                # Average Copy GB/s 35.172220
                # Maximum Copy GB/s 35.172220
                # Minimum Scale GB/s 33.287994
                # Average Scale GB/s 33.287994
                # Maximum Scale GB/s 33.287994
                # Minimum Add GB/s 30.727379
                # Average Add GB/s 30.727379
                # Maximum Add GB/s 30.727379
                # Minimum Triad GB/s 29.852578
                # Average Triad GB/s 29.852578
                # Maximum Triad GB/s 29.852578
            # SingleSTREAM
                # Single STREAM Copy GB/s 69.904787
                # Single STREAM Scale GB/s 66.575988
                # Single STREAM Add GB/s 60.786771
                # Single STREAM Triad GB/s 60.786771
        #  PTRANS
            # TIME   M     N    MB  NB  P   Q     TIME   CHECK   GB/s   RESID
            # ---- ----- ----- --- --- --- --- -------- ------ -------- -----
            # WALL   500   500  80  80   2   2     0.00 PASSED    4.726  0.00
        #  RandomAccess:
            # MPIRandomAccess / MPIRandomAccess_LCG
                # 0.001405858 Billion(10^9) Updates    per second [GUP/s]
                # 0.000351464 Billion(10^9) Updates/PE per second [GUP/s]
            # SingleRandomAccess / SingleRandomAccess_LCG
                # Single GUP/s 0.724316
            # StarRandomAccess / StarRandomAccess_LCG
                # Minimum GUP/s 0.380717
                # Average GUP/s 0.453077
                # Maximum GUP/s 0.661958
        #  FFT
            # SingleFFT
                # Single FFT Gflop/s 5.151385
            # MPIFFT
                # Gflop/s:     7.768
            # StarFFT
                # Minimum Gflop/s 4.609983
                # Average Gflop/s 4.761104
                # Maximum Gflop/s 4.903864
        #  LatencyBandwidth
            # Max Ping Pong Latency:                 0.000489 msecs
            # Randomly Ordered Ring Latency:         0.000425 msecs
            # Min Ping Pong Bandwidth:           10958.338341 MB/s
            # Naturally Ordered Ring Bandwidth:  13421.772800 MB/s
            # Randomly  Ordered Ring Bandwidth:  12860.856132 MB/s
    '''
