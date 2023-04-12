# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Lulesh(SpackApplication):
    '''Define LULESH application'''
    name = 'LULESH'

    tags = ['proxy-app', 'mini-app']

    default_compiler('intel202160', base='intel-oneapi-compilers', version='2022.1.0',
                     custom_specifier='intel@2021.6.0')

    mpi_library('impi2018', base='intel-mpi', version='2018.4.274')

    software_spec('lulesh', base='lulesh', version='2.0.3',
                  variants='+openmp',
                  compiler='intel202160', mpi='impi2018', required=True)

    executable('execute', 'lulesh2.0 {flags}', use_mpi=True)

    workload('standard', executables=['execute'])

    workload_variable('size_flag', default='',
                      description='Problem size in a single dimension. Real problem is size^3. Needs to be prefixed by -s',
                      workloads=['standard'])

    workload_variable('iteration_flag', default='',
                      description='Fixed number of iterations to perform. Needs to be prefixed by -i',
                      workloads=['standard'])

    workload_variable('flags', default='{size_flag} {iteration_flag}',
                      description='Flags to pass in to LULESH',
                      workloads=['standard'])

    figure_of_merit('Time', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'\s*Elapsed time\s+=\s+(?P<time>[0-9]+\.[0-9]+).*',
                    group_name='time', units='s')

    figure_of_merit('FOM', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'\s*FOM\s+=\s+(?P<fom>[0-9]+\.[0-9]+).*',
                    group_name='fom', units='z/s')

    figure_of_merit('Size', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'\s*Problem size\s+=\s+(?P<size>[0-9]+)',
                    group_name='size', units='')

    figure_of_merit('Grind Time', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'\s*Grind time \(us/z/c\)\s+=\s+(?P<grind>[0-9]+\.[0-9]+).*',
                    group_name='grind', units='s/element')

    figure_of_merit('NumTasks', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'\s*MPI tasks\s+=\s+(?P<tasks>[0-9]+)',
                    group_name='tasks', units='')

    figure_of_merit('Iterations', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'\s*Iteration count\s+=\s+(?P<iterations>[0-9]+)',
                    group_name='iterations', units='')

    def _make_experiments(self, workspace):
        """
        LULESH requires the number of ranks to be a cube root of an integer.

        Here we compute the closest integer equal to or larger than the target
        number of ranks.

        We also need to recompute the number of nodes, or the value of
        processes per node here too.
        """
        num_ranks = int(self.expander.expand_var('{n_ranks}'))

        cube_root = int(num_ranks ** (1. / 3.))

        self.variables['n_ranks'] = cube_root**3

        super()._make_experiments(workspace)
