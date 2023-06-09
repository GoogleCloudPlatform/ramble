# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Iperf2(SpackApplication):
    '''Define the iperf2 application'''
    name = 'iperf2'

    maintainers('rfbgo')

    default_compiler('gcc9', spack_spec='gcc@9.3.0')

    software_spec('iperf2',
                  spack_spec='iperf2@2.0.12',
                  compiler='gcc9')

    required_package('iperf2')

    # Need to support these use cases:
    # iperf -s // set up server
    # iperf -t 600 -i 10 -c server_dns_or_internal_ip -P 16 // connect from another vm
    workload('iperf2_server', executable='iperf2')
    workload('iperf2_client', executable='iperf2')
    workload('iperf2_custom', executable='iperf2')

    workload_variable('input_flags',
                      default='-s',
                      description='Input flags to start iperf2 in server mode',
                      workload='iperf2_server')

    workload_variable('input_flags',
                      default='-t {time} -i {interval} -c {host} -P {num_threads}',
                      description='Input flags to start iperf2 in server mode',
                      workload='iperf2_client')

    workload_variable('input_flags',
                      default='',
                      description='Input flags in custom mode',
                      workload='iperf2_custom')

    workload_variable('time',
                      default='600',
                      description='time in seconds to listen for new connections as well as to receive traffic (default not set)',
                      workload='iperf2_client')

    workload_variable('interval',
                      default='10',
                      description='seconds between periodic bandwidth reports',
                      workload='iperf2_client')

    workload_variable('host',
                      default='<host>',
                      description='run in client mode, connecting to <host>',
                      workload='iperf2_client')

    workload_variable('num_threads',
                      default='16',
                      description='number of parallel client threads to run',
                      workload='iperf2_client')

    workload_variable('additional_flags',
                      default='',
                      description='Allow users to pass additional flags',
                      workloads=['iperf2_client', 'iperf2_server', 'iperf2_custom'])

    executable('iperf2',
               template='iperf {input_flags} {additional_flags}',
               use_mpi=False)

    # TODO: addsuccess_criteria(..
    figure_of_merit(
        'Total BW',
        log_file='{experiment_run_dir}/{experiment_name}.out',
        fom_regex=r'\[SUM\]\s.*sec\s.*GBytes\s(?P<bw>.*)\sGbits/sec.*',
        group_name='bw',
        units='Gbits/sec'
    )
