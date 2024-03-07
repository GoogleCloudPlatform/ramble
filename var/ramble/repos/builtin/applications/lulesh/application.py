# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *
from ramble.expander import Expander


class Lulesh(SpackApplication):
    '''Define LULESH application'''
    name = 'LULESH'

    maintainers('douglasjacobsen')

    tags('proxy-app', 'mini-app')

    define_compiler('gcc13', spack_spec='gcc@13.1.0')

    software_spec('impi2018',
                  spack_spec='intel-mpi@2018.4.274')

    software_spec('lulesh',
                  spack_spec='lulesh@2.0.3 +openmp',
                  compiler='gcc13')

    required_package('lulesh')

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

    log_str = os.path.join(Expander.expansion_str('experiment_run_dir'),
                           Expander.expansion_str('experiment_name') + '.out')

    figure_of_merit('Time', log_file=log_str,
                    fom_regex=r'\s*Elapsed time\s+=\s+(?P<time>[0-9]+\.[0-9]+).*',
                    group_name='time', units='s')

    figure_of_merit('FOM', log_file=log_str,
                    fom_regex=r'\s*FOM\s+=\s+(?P<fom>[0-9]+\.[0-9]+).*',
                    group_name='fom', units='z/s')

    figure_of_merit('Size', log_file=log_str,
                    fom_regex=r'\s*Problem size\s+=\s+(?P<size>[0-9]+)',
                    group_name='size', units='')

    figure_of_merit('Grind Time', log_file=log_str,
                    fom_regex=r'\s*Grind time \(us/z/c\)\s+=\s+(?P<grind>[0-9]+\.[0-9]+).*',
                    group_name='grind', units='s/element')

    figure_of_merit('NumTasks', log_file=log_str,
                    fom_regex=r'\s*MPI tasks\s+=\s+(?P<tasks>[0-9]+)',
                    group_name='tasks', units='')

    figure_of_merit('Iterations', log_file=log_str,
                    fom_regex=r'\s*Iteration count\s+=\s+(?P<iterations>[0-9]+)',
                    group_name='iterations', units='')

    def _make_experiments(self, workspace, app_inst=None):
        """
        LULESH requires the number of ranks to be a cube root of an integer.

        Here we compute the closest integer equal to or larger than the target
        number of ranks.

        We also need to recompute the number of nodes, or the value of
        processes per node here too.
        """
        num_ranks = int(self.expander.expand_var_name('n_ranks'))

        cube_root = int(num_ranks ** (1. / 3.))

        self.variables['n_ranks'] = cube_root**3

        super()._make_experiments(workspace)
