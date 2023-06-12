# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

# Genral Guidance:
# - Use compact placement policy
# - Check the compute nodes in a single rack using the network topology API


class IntelMpiBenchmarks(SpackApplication):
    '''Intel MPI Benchmark application.

    https://www.intel.com/content/www/us/en/developer/articles/technical/intel-mpi-benchmarks.html
    https://github.com/intel/mpi-benchmarks
    https://www.intel.com/content/www/us/en/develop/documentation/imb-user-guide/top.html
    '''

    name = 'IntelMpiBenchmarks'

    maintainers('rfbgo')

    tags('micro-benchmark', 'benchmark', 'mpi')

    default_compiler('gcc9', spack_spec='gcc@9.3.0')
    software_spec('impi2018', spack_spec='intel-mpi@2018.4.274')
    software_spec('intel-mpi-benchmarks',
                  spack_spec='intel-mpi-benchmarks@2019.6',
                  compiler='gcc9')

    required_package('intel-mpi-benchmarks')

    executable('pingpong',
               '-genv I_MPI_FABRICS=shm:tcp '
               '-genv I_MPI_PIN_PROCESSOR_LIST=0 '
               'IMB-MPI1 {pingpong_type} -msglog {msglog_min}:{msglog_max} '
               '-iter {num_iterations} -show_tail on -dumpfile {output_file}',
               use_mpi=True)

    # FIXME: how best to deal with the desirded behavior of <2*num_cores> -ppn <num_cores>
    executable('multi-pingpong',
               '-genv I_MPI_FABRICS=shm:tcp '
               'IMB-MPI1 Pingpong -msglog {msglog_min}:{msglog_max} '
               '-iter {num_iteration} -multi 0 -map 2*{num_cores} -show_tail on',
               use_mpi=True)

    executable('collective',
               '-genv I_MPI_FABRICS=shm:tcp '
               'IMB-MPI1 {collective_type} -msglog {msglog_min}:{msglog_max} '
               '-iter {num_iterations} -npmin {min_collective_ranks}',
               use_mpi=True)

    workload('pingpong', executable='pingpong')
    workload('multi-pingpong', executable='multi-pingpong')
    workload('collective', executable='collective')

    workload_variable('output_path', default='./output',
                      description='Dumpfile Output Path',
                      workloads=['pingpong'])

    workload_variable('pingpong_type',
                      default='Pingpong',
                      values=['Pingpong', 'Unirandom', 'Multi-Pingpong', 'Birandom', 'Corandom'],
                      description='Pingpong Algorithm to Use',
                      workloads=['pingpong'])

    workload_variable('num_cores',
                      default='{n_ranks}/2',
                      description='Number of cores',
                      workloads=['multi-pingpong'])

    workload_variable('collective_type',
                      # FIXME: should default just be denoted by the
                      # first value in the values list?
                      default='Allgather',
                      values=['Allgather', 'Allgatherv', 'Alltoall',
                              'Alltoallv', 'Bcast', 'Scatter', 'Scatterv',
                              'Gather', 'Gatherv', 'Reduce', 'Reduce_scatter',
                              'Allreduce', 'Barrier'],
                      description='Collective type to test',
                      workloads=['collective'])

    workload_variable('min_collective_ranks', default='{n_ranks}',
                      description='Minimum number of ranks to use in a collective operation',
                      workloads=['collective'])

    workload_variable('num_iterations', default='1000',
                      description='Number of iterations to test over',
                      workloads=['pingpong', 'multi-pingpong', 'collective'])

    workload_variable('msglog_min', default='1',
                      description='Min Message Size (power of 2)',
                      workloads=['pingpong', 'multi-pingpong', 'collective'])

    workload_variable('msglog_max', default='30',
                      description='Max Message Size (power of 2)',
                      workloads=['pingpong', 'multi-pingpong', 'collective'])

    # Matches tables like:
    #  bytes #repetitions  t_min[usec]  t_max[usec]  t_avg[usec]
    latency_regex = r'^\s+(?P<bytes>\d+)\s+(?P<repetitions>\d+)\s+' + \
                    r'(?P<t_min>\d+\.\d+)\s+(?P<t_avg>\d+\.\d+)\s+(?P<t_max>\d+\.\d+)$'

    figure_of_merit('Latency min', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=latency_regex,
                    group_name='t_min', units='usec', contexts=['latency-bytes'])

    figure_of_merit('Latency avg', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=latency_regex,
                    group_name='t_avg', units='usec', contexts=['latency-bytes'])

    figure_of_merit('Latency max', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=latency_regex,
                    group_name='t_max', units='usec', contexts=['latency-bytes'])

    # Matches tables like:
    #  bytes #repetitions      t[usec]   Mbytes/sec
    bw_regex = r'^\s+(?P<bytes>\d+)\s+(?P<repetitions>\d+)\s+(?P<t_avg>\d+\.\d+)\s+(?P<bw>\d+\.\d+)$'
    figure_of_merit('Bandwidth', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=bw_regex,
                    group_name='bw', units='Mbytes/sec', contexts=['bw-bytes'])

    # Combiend tables like:
    #  bytes #repetitions  t_min[usec]  t_max[usec]  t_avg[usec]   Mbytes/sec
    #   (happens in sendrecv and exchange)
    combined_regex = r'^\s+(?P<bytes>\d+)\s+(?P<repetitions>\d+)\s+' + \
                     r'(?P<t_min>\d+\.\d+)\s+(?P<t_avg>\d+\.\d+)\s+' + \
                     r'(?P<t_max>\d+\.\d+)\s+(?P<bw>\d+\.\d+)$'
    figure_of_merit('Combo', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=combined_regex,
                    group_name='bw', units='Mbytes/sec', contexts=['combo-bytes'])

    figure_of_merit_context('latency-bytes',
                            regex=latency_regex,
                            output_format='Bytes: {bytes} (Latency)')

    figure_of_merit_context('bw-bytes',
                            regex=bw_regex,
                            output_format='Bytes: {bytes} (BW)')

    figure_of_merit_context('combo-bytes',
                            regex=combined_regex,
                            output_format='Bytes: {bytes} (Combo)')
