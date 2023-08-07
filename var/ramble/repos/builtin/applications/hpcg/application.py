# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *
from ramble.expander import Expander


class Hpcg(SpackApplication):
    '''Define HPCG application'''
    name = 'hpcg'

    maintainers('douglasjacobsen')

    tags('benchmark', 'benchmark-app', 'mini-app', 'miniapp', 'linear-algebra')

    default_compiler('gcc9', spack_spec='gcc@9.3.0')

    software_spec('impi2018',
                  spack_spec='intel-mpi@2018.4.274')

    software_spec('hpcg',
                  spack_spec='hpcg@3.1 +openmp',
                  compiler='gcc9')

    required_package('hpcg')

    executable('execute', 'xhpcg', use_mpi=True)

    executable('move-log', 'mv HPCG-Benchmark*.txt {out_file}',
               use_mpi=False)

    workload('standard', executables=['execute', 'move-log'])

    workload_variable('matrix_size', default='104 104 104',
                      description='Dimensions of the matrix to use',
                      workloads=['standard'])

    workload_variable('iterations', default='60',
                      description='Number of iterations to perform',
                      workloads=['standard'])

    workload_variable('out_file', default='{experiment_run_dir}/hpcg_result.out',
                      description='Output file for results',
                      workloads=['standard'])

    log_str = Expander.expansion_str('out_file')

    figure_of_merit('Status', log_file=log_str,
                    fom_regex=r'Final Summary::HPCG result is (?P<status>[a-zA-Z]+) with a GFLOP/s rating of=(?P<gflops>[0-9]+\.[0-9]+)',
                    group_name='status', units='')

    figure_of_merit('Gflops', log_file=log_str,
                    fom_regex=r'Final Summary::HPCG result is (?P<status>[a-zA-Z]+) with a GFLOP/s rating of=(?P<gflops>[0-9]+\.[0-9]+)',
                    group_name='gflops', units='GFLOP/s')

    figure_of_merit('Time', log_file=log_str,
                    fom_regex=r'Final Summary::Results are.* execution time.*is=(?P<exec_time>[0-9]+\.[0-9]*)',
                    group_name='exec_time', units='s')

    figure_of_merit('ComputeDotProductMsg', log_file=log_str,
                    fom_regex=r'Final Summary::Reference version of ComputeDotProduct used.*=(?P<msg>.*)',
                    group_name='msg', units='')

    figure_of_merit('ComputeSPMVMsg', log_file=log_str,
                    fom_regex=r'Final Summary::Reference version of ComputeSPMV used.*=(?P<msg>.*)',
                    group_name='msg', units='')

    figure_of_merit('ComputeMGMsg', log_file=log_str,
                    fom_regex=r'Final Summary::Reference version of ComputeMG used.*=(?P<msg>.*)',
                    group_name='msg', units='')

    figure_of_merit('ComputeWAXPBYMsg', log_file=log_str,
                    fom_regex=r'Final Summary::Reference version of ComputeWAXPBY used.*=(?P<msg>.*)',
                    group_name='msg', units='')

    figure_of_merit('HPCG 2.4 Rating', log_file=log_str,
                    fom_regex=r'Final Summary::HPCG 2\.4 rating.*=(?P<rating>[0-9]+\.*[0-9]*)',
                    group_name='rating', units='')

    def _make_experiments(self, workspace):
        super()._make_experiments(workspace)

        input_path = os.path.join(self.expander.expand_var_name('experiment_run_dir'),
                                  'hpcg.dat')

        with open(input_path, 'w+') as f:
            f.write('HPCG benchmark input file\n')
            f.write('Sandia National Laboratories; University of Tennessee, Knoxville\n')
            f.write(self.expander.expand_var_name('matrix_size') + '\n')
            f.write(self.expander.expand_var_name('iterations') + '\n')
