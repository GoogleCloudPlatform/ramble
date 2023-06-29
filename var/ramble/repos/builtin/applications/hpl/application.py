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

    maintainers('douglasjacobsen', 'dodecatheon')

    tags('benchmark-app', 'benchmark', 'linpack')

    default_compiler('gcc9', spack_spec='gcc@9.3.0')

    software_spec('impi_2018', spack_spec='intel-mpi@2018.4.274')

    software_spec('hpl', spack_spec='hpl@2.3 +openmp', compiler='gcc9')

    required_package('hpl')

    executable('execute', 'xhpl', use_mpi=True)

    workload('standard', executables=['execute'])
    workload('calculator', executables=['execute'])

    workload_variable('output_file',
                      default='{:13} output file name (if any)'.format('HPL.out'),
                      description='Output file name (if any)',
                      workloads=['standard'])
    workload_variable('device_out',
                      default='{:13} device out (6=stdout,7=stderr,file)'.format('6'),
                      description='Output device',
                      workloads=['standard'])
    workload_variable('N-Ns',
                      default='{:13} Number of problems sizes (N)'.format('4'),
                      description='Number of problems sizes',
                      workloads=['standard'])
    workload_variable('Ns',
                      default='{:13} Ns'.format('29 30 34 35'),
                      description='Problem sizes',
                      workloads=['standard'])
    workload_variable('N-NBs',
                      default='{:13} Number of NBs'.format('4'),
                      description='Number of NBs',
                      workloads=['standard'])
    workload_variable('NBs',
                      default='{:13} NBs'.format('1 2 3 4'),
                      description='NB values',
                      workloads=['standard'])
    workload_variable('PMAP',
                      default='{:13} PMAP process mapping (0=Row-,1=Column-major)'.format('0'),
                      description='PMAP Process mapping. (0=Row-, 1=Column-Major)',
                      workloads=['standard'])
    workload_variable('N-Grids',
                      default='{:13} Number of process grids (P x Q)'.format('3'),
                      description='Number of process grids (P x Q)',
                      workloads=['standard'])
    workload_variable('Ps',
                      default='{:13} Ps'.format('2 1 4'),
                      description='P values',
                      workloads=['standard'])
    workload_variable('Qs',
                      default='{:13} Qs'.format('2 4 1'),
                      description='Q values',
                      workloads=['standard'])
    workload_variable('threshold',
                      default='{:13} threshold'.format('16.0'),
                      description='Residual threshold',
                      workloads=['standard'])
    workload_variable('NPFACTs',
                      default='{:13} Number of PFACTs, panel fact'.format('3'),
                      description='Number of PFACTs',
                      workloads=['standard'])
    workload_variable('PFACTs',
                      default='{:13} PFACTs (0=left, 1=Crout, 2=Right)'.format('0 1 2'),
                      description='PFACT Values',
                      workloads=['standard'])
    workload_variable('N-NBMINs',
                      default='{:13} Number of NBMINs, recursive stopping criteria'.format('2'),
                      description='Number of NBMINs',
                      workloads=['standard'])
    workload_variable('NBMINs',
                      default='{:13} NBMINs (>= 1)'.format('2 4'),
                      description='NBMIN values',
                      workloads=['standard'])
    workload_variable('N-NDIVs',
                      default='{:13} Number of NDIVs, panels in recursion'.format('1'),
                      description='Number of NDIVs',
                      workloads=['standard'])
    workload_variable('NDIVs',
                      default='{:13} NDIVs'.format('2'),
                      description='NDIV values',
                      workloads=['standard'])
    workload_variable('N-RFACTs',
                      default='{:13} Number of RFACTs, recursive panel fact.'.format('3'),
                      description='Number of RFACTs',
                      workloads=['standard'])
    workload_variable('RFACTs',
                      default='{:13} RFACTs (0=left, 1=Crout, 2=Right)'.format('0 1 2'),
                      description='RFACT values',
                      workloads=['standard'])
    workload_variable('N-BCASTs',
                      default='{:13} Number of BCASTs, broadcast'.format('1'),
                      description='Number of BCASTs',
                      workloads=['standard'])
    workload_variable('BCASTs',
                      default='{:13} BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM)'.format('0'),
                      description='BCAST values',
                      workloads=['standard'])
    workload_variable('N-DEPTHs',
                      default='{:13} Number of DEPTHs, lookahead depth'.format('1'),
                      description='Number of DEPTHs',
                      workloads=['standard'])
    workload_variable('DEPTHs',
                      default='{:13} DEPTHs (>=0)'.format('0'),
                      description='DEPTH values',
                      workloads=['standard'])
    workload_variable('SWAP',
                      default='{:13} SWAP (0=bin-exch,1=long,2=mix)'.format('2'),
                      description='Swapping algorithm',
                      workloads=['standard'])
    workload_variable('swapping_threshold',
                      default='{:13} swapping threshold'.format('64'),
                      description='Swapping threshold',
                      workloads=['standard'])
    workload_variable('L1',
                      default='{:13} L1 in (0=transposed,1=no-transposed) form'.format('0'),
                      description='Storage for upper triangular portion of columns',
                      workloads=['standard'])
    workload_variable('U',
                      default='{:13} U  in (0=transposed,1=no-transposed) form'.format('0'),
                      description='Storage for the rows of U',
                      workloads=['standard'])
    workload_variable('Equilibration',
                      default='{:13} Equilibration (0=no,1=yes)'.format('1'),
                      description='Determines if equilibration should be enabled or disabled.',
                      workloads=['standard'])
    workload_variable('mem_alignment',
                      default='{:13} memory alignment in double (> 0)'.format('8'),
                      description='Sets the alignment in doubles for memory addresses',
                      workloads=['standard'])

    # calculator workload-specific variables:

    workload_variable('percent_mem', default='85',
                      description='Percent of memory to use (default 85)',
                      workloads=['calculator'])

    workload_variable('memory_per_node',
                      default='240',
                      description='Memory per node in GB',
                      workloads=['calculator'])

    workload_variable('block_size', default='384',
                      description='Size of each block',
                      workloads=['calculator'])

    workload_variable('pfact',
                      default='0',
                      description='PFACT for optimized calculator',
                      workloads=['calculator'])

    workload_variable('nbmin',
                      default='2',
                      description='NBMIN for optimized calculator',
                      workloads=['calculator'])

    workload_variable('rfact',
                      default='0',
                      description='RFACT for optimized calculator',
                      workloads=['calculator'])

    workload_variable('bcast',
                      default='0',
                      description='BCAST for optimized calculator',
                      workloads=['calculator'])

    workload_variable('depth',
                      default='0',
                      description='DEPTH for optimized calculator',
                      workloads=['calculator'])

    # FoMs:

    figure_of_merit('Time', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'.*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n',
                    group_name='time', units='s', contexts=['problem-name'])

    figure_of_merit('GFlops', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'.*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n',
                    group_name='gflops', units='GFLOP/s',
                    contexts=['problem-name'])

    figure_of_merit_context('problem-name', regex=r'.*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n', output_format='{N}-{NB}-{P}-{Q}')

    # Integer sqrt
    def _isqrt(self, n):
        if n < 0:
            raise Exception
        elif n < 2:
            return (n)
        else:
            lo = self._isqrt(n >> 2) << 1
            hi = lo + 1
            if ((hi * hi) > n):
                return (lo)
            else:
                return (hi)

    def _calculate_values(self, workspace, expander):
        if expander.workload_name == 'calculator':
            # Find the best P and Q whose product is the number of available
            # cores, with P less than Q
            nNodes = int(expander.expand_var('{n_nodes}'))
            processesPerNode = int(expander.expand_var('{processes_per_node}'))

            totalCores = nNodes * processesPerNode

            bestP = self._isqrt(totalCores)
            while ((totalCores % bestP) > 0):     # stops at 1 because any int % 1 = 0
                bestP -= 1

            bestQ = totalCores // bestP

            # Find LCM(P,Q)
            P = int(bestP)
            Q = int(bestQ)
            lcmPQ = Q             # Q is always the larger of P and Q
            while ((lcmPQ % P) > 0):
                lcmPQ += Q

            # HPL maintainers recommend basing the target problem size on
            # the square root of 80% of total memory in words.
            memoryPerNode = int(expander.expand_var('{memory_per_node}'))
            memFraction = int(expander.expand_var('{percent_mem}')) / 100
            blockSize = int(expander.expand_var('{block_size}'))
            one_gb_mem_in_words = (1 << 30) / 8

            fullMemWords = nNodes * memoryPerNode * one_gb_mem_in_words

            targetProblemSize = math.sqrt(fullMemWords * memFraction)

            # Ensure that N is divisible by NB * LCM(P,Q)
            problemSize = int(targetProblemSize)
            problemSize -= (problemSize % blockSize)
            nBlocks = problemSize // blockSize
            nBlocks -= nBlocks % lcmPQ
            problemSize = blockSize * nBlocks
            usedPercentage = int(problemSize**2 / fullMemWords * 100)

            for var, config in self.workload_variables['standard'].items():
                self.variables[var] = config['default']

            pfact = expander.expand_var('{pfact}')
            nbmin = expander.expand_var('{nbmin}')
            rfact = expander.expand_var('{rfact}')
            bcast = expander.expand_var('{bcast}')
            depth = expander.expand_var('{depth}')

            self.variables['N-Ns'] = '{:13} Number of problems sizes (N)'.format('1')  # vs 4

            # Calculated:
            self.variables['Ns'] = ("{:<13} Ns (= {}% of "
                                    "total available memory)").format(int(problemSize),
                                                                      usedPercentage)
            self.variables['N-NBs'] = '{:13} Number of NBs'.format('1')  # vs 4

            # Calculated:
            self.variables['NBs'] = "{:<13} NBs".format(blockSize)  # calculated, vs 4 samples

            self.variables['N-Grids'] = ('{:13} Number of Grids,'
                                         'process grids (P x Q)').format('1')  # vs 3
            # Calculated:
            self.variables['Ps'] = "{:<13} Ps".format(int(bestP))

            # Calculated:
            self.variables['Qs'] = "{:<13} Qs".format(int(bestQ))

            self.variables['NPFACTs'] = '{:13} Number of PFACTs, panel fact'.format('1')  # vs 3

            # ramble.yaml configurable
            self.variables['PFACTs'] = '{:13} PFACT Values (0=left, 1=Crout, 2=Right)'.format(pfact)  # vs 0 1 2

            self.variables['N-NBMINs'] = '{:13} Number of NBMINs, recursive stopping criteria'.format('1')  # vs 2

            # ramble.yaml configurable
            self.variables['NBMINs'] = '{:13} NBMINs (>= 1)'.format(nbmin)  # vs '2 4'

            self.variables['N-RFACTs'] = '{:13} Number of RFACTS, recursive panel fact.'.format('1')  # vs '3'

            # ramble.yaml configurable
            self.variables['RFACTs'] = '{:13} RFACTs (0=left, 1=Crout, 2=Right)'.format(rfact)  # vs '0 1 2'

            self.variables['N-BCASTs'] = '{:13} Number of BCASTs, broadcast'.format('1')

            # ramble.yaml configurable
            self.variables['BCASTs'] = ('{:13} BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,'
                                        '5=LnM,6=MKL BPUSH,7=AMD Hybrid Panel)').format(bcast)  # vs '0'

            self.variables['N-DEPTHs'] = '{:13} Number of DEPTHs, lookahead depth'.format('1')

            # ramble.yaml configurable
            self.variables['DEPTHs'] = '{:13} DEPTHs (>=0)'.format(depth)  # vs '0'

    def _make_experiments(self, workspace):
        super()._make_experiments(workspace)
        self._calculate_values(workspace, self.expander)

        input_path = self.expander.expand_var('{experiment_run_dir}/HPL.dat')

        settings = ['output_file', 'device_out', 'N-Ns', 'Ns', 'N-NBs', 'NBs',
                    'PMAP', 'N-Grids', 'Ps', 'Qs', 'threshold', 'NPFACTs',
                    'PFACTs', 'N-NBMINs', 'NBMINs', 'N-NDIVs', 'NDIVs', 'N-RFACTs',
                    'RFACTs', 'N-BCASTs', 'BCASTs', 'N-DEPTHs', 'DEPTHs', 'SWAP',
                    'swapping_threshold', 'L1', 'U', 'Equilibration',
                    'mem_alignment']

        with open(input_path, 'w+') as f:
            f.write('    HPLinpack benchmark input file\n')
            f.write('Innovative Computing Laboratory, University of Tennessee\n')

            for setting in settings:
                f.write(self.expander.expand_var('{' + setting + '}') + '\n')

            # Write some documentation at the bottom of the input file:
            f.write('##### This line (no. 32) is ignored (it serves as a separator). ######')
