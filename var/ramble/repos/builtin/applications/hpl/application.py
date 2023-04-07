# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *

import math


class Hpl(SpackApplication):
    '''Define HPL application'''
    name = 'hpl'

    tags = ['benchmark-app', 'mini-app', 'benchmark']

    default_compiler('gcc9', base='gcc', version='9.3.0')

    mpi_library('impi2018', base='intel-mpi', version='2018.4.274')

    software_spec('hpl', base='hpl', version='2.3',
                  variants='+openmp',
                  compiler='gcc9', mpi='impi2018', required=True)

    executable('execute', 'xhpl', use_mpi=True)

    workload('standard', executables=['execute'])

    workload_variable('output_file', default='HPL.out      output file name (if any)',
                      description='Output file name (if any)',
                      workloads=['standard'])
    workload_variable('device_out', default='6            device out (6=stdout,7=stderr,file)',
                      description='Output device',
                      workloads=['standard'])
    workload_variable('N-Ns', default='4            # of problems sizes (N)',
                      description='Number of problems sizes',
                      workloads=['standard'])
    workload_variable('Ns', default='29 30 34 35  Ns',
                      description='Problem sizes',
                      workloads=['standard'])
    workload_variable('N-NBs', default='4            # of NBs',
                      description='Number of NBs',
                      workloads=['standard'])
    workload_variable('NBs', default='1 2 3 4      NBs',
                      description='NB values',
                      workloads=['standard'])
    workload_variable('PMAP', default='0            PMAP process mapping (0=Row-,1=Column-major)',
                      description='PMAP Process mapping. (0=Row-, 1=Column-Major)',
                      workloads=['standard'])
    workload_variable('N-Grids', default='3            # of process grids (P x Q)',
                      description='Number of process grids (P x Q)',
                      workloads=['standard'])
    workload_variable('Ps', default='2 1 4        Ps',
                      description='P values',
                      workloads=['standard'])
    workload_variable('Qs', default='2 4 1        Qs',
                      description='Q values',
                      workloads=['standard'])
    workload_variable('threshold', default='16.0         threshold',
                      description='Residual threshold',
                      workloads=['standard'])
    workload_variable('NPFACTS', default='3            # of panel fact',
                      description='Number of PFACTs',
                      workloads=['standard'])
    workload_variable('PFACTS', default='0 1 2        PFACTs (0=left, 1=Crout, 2=Right)',
                      description='PFACT Values',
                      workloads=['standard'])
    workload_variable('N-NBMINs', default='2            # of recursive stopping criterium',
                      description='Number of NBMINs',
                      workloads=['standard'])
    workload_variable('NBMINs', default='2 4          NBMINs (>= 1)',
                      description='NBMIN values',
                      workloads=['standard'])
    workload_variable('N-NDIVs', default='1            # of panels in recursion',
                      description='Number of NDIVs',
                      workloads=['standard'])
    workload_variable('NDIVs', default='2            NDIVs',
                      description='NDIV values',
                      workloads=['standard'])
    workload_variable('N-RFACTs', default='3            # of recursive panel fact.',
                      description='Number of RFACTs',
                      workloads=['standard'])
    workload_variable('RFACTs', default='0 1 2        RFACTs (0=left, 1=Crout, 2=Right)',
                      description='RFACT values',
                      workloads=['standard'])
    workload_variable('N-BCASTs', default='1            # of broadcast',
                      description='Number of BCASTs',
                      workloads=['standard'])
    workload_variable('BCASTs', default='0            BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM)',
                      description='BCAST values',
                      workloads=['standard'])
    workload_variable('N-DEPTHs', default='1            # of lookahead depth',
                      description='Number of DEPTHs',
                      workloads=['standard'])
    workload_variable('DEPTHs', default='0            DEPTHs (>=0)',
                      description='DEPTH values',
                      workloads=['standard'])
    workload_variable('SWAP', default='2            SWAP (0=bin-exch,1=long,2=mix)',
                      description='Swapping algorithm',
                      workloads=['standard'])
    workload_variable('swapping_threshold', default='64           swapping threshold',
                      description='Swapping threshold',
                      workloads=['standard'])
    workload_variable('L1', default='0            L1 in (0=transposed,1=no-transposed) form',
                      description='Storage for upper triangular portion of columns',
                      workloads=['standard'])
    workload_variable('U', default='0            U  in (0=transposed,1=no-transposed) form',
                      description='Storage for the rows of U',
                      workloads=['standard'])
    workload_variable('Equilibration', default='1            Equilibration (0=no,1=yes)',
                      description='Determines if equilibration should be enabled or disabled.',
                      workloads=['standard'])
    workload_variable('mem_alignment', default='8            memory alignment in double (> 0)',
                      description='Sets the alignment in doubles for memory addresses',
                      workloads=['standard'])

    workload('calculator', executables=['execute'])

    workload_variable('memory_per_node', default='128',
                      description='Memory per node in GB',
                      workloads=['calculator'])

    workload_variable('block_size', default='224',
                      description='Size of each block',
                      workloads=['calculator'])

    figure_of_merit('Time', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'.*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n',
                    group_name='time', units='s', contexts=['problem-name'])

    figure_of_merit('GFlops', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'.*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n',
                    group_name='gflops', units='GFLOP/s',
                    contexts=['problem-name'])

    figure_of_merit_context('problem-name', regex=r'.*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n', output_format='{N}-{NB}-{P}-{Q}')

    def _calculate_values(self, workspace, expander):
        if expander.workload_name == 'calculator':
            memoryPerNode = int(expander.expand_var('{memory_per_node}'))
            nNodes = int(expander.expand_var('{n_nodes}'))
            processesPerNode = int(expander.expand_var('{processes_per_node}'))
            blockSize = int(expander.expand_var('{block_size}'))

            targetProblemSize = 0.80 * int(math.sqrt((memoryPerNode
                                           * nNodes * 1024 * 1024 * 1024)
                                           / 8))
            nBlocks = int(targetProblemSize / blockSize)
            nBlocks = nBlocks if (nBlocks % 2 == 0) else nBlocks - 1
            problemSize = blockSize * nBlocks

            totalCores = nNodes * processesPerNode
            sqrtCores = int(math.sqrt(totalCores))

            bestDist = totalCores - 1
            bestP = 1

            for i in range(2, sqrtCores):
                if totalCores % i == 0:
                    testDist = totalCores - i
                    if testDist < bestDist:
                        bestDist = testDist
                        bestP = i

            bestQ = int(totalCores / bestP)

            for var, config in self.workload_variables['standard'].items():
                expander.set_var(var, config['default'])

            expander.set_var('N-Ns', '1')
            expander.set_var('Ns', int(problemSize))
            expander.set_var('N-NBs', '1')
            expander.set_var('NBs', blockSize)
            expander.set_var('N-Grids', '1')
            expander.set_var('Ps', int(bestP))
            expander.set_var('Qs', int(bestQ))
            expander.set_var('NPFACTS', '1')
            expander.set_var('PFACTS', '2')
            expander.set_var('N-NBMINs', '1')
            expander.set_var('NBMINs', '4')
            expander.set_var('N-RFACTs', '1')
            expander.set_var('RFACTs', '1')
            expander.set_var('N-BCASTs', '1')
            expander.set_var('BCASTs', '1')
            expander.set_var('N-DEPTHs', '1')
            expander.set_var('DEPTHs', '1')

    def _make_experiments(self, workspace):
        super()._make_experiments(workspace)
        self._calculate_values(workspace, self.expander)

        input_path = self.expander.expand_var('{experiment_run_dir}/HPL.dat')

        settings = ['output_file', 'device_out', 'N-Ns', 'Ns', 'N-NBs', 'NBs',
                    'PMAP', 'N-Grids', 'Ps', 'Qs', 'threshold', 'NPFACTS',
                    'PFACTS', 'N-NBMINs', 'NBMINs', 'N-NDIVs', 'NDIVs', 'N-RFACTs',
                    'RFACTs', 'N-BCASTs', 'BCASTs', 'N-DEPTHs', 'DEPTHs', 'SWAP',
                    'swapping_threshold', 'L1', 'U', 'Equilibration',
                    'mem_alignment']

        with open(input_path, 'w+') as f:
            f.write('    HPLinpack benchmark input file\n')
            f.write('Innovative Computing Laboratory, University of Tennessee\n')

            for setting in settings:
                f.write(self.expander.expand_var('{' + setting + '}') + '\n')
