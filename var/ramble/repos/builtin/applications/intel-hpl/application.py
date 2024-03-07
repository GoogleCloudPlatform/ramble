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

import math


def pad_value(val, desc):
    return ('{:<14}'.format(val) + desc)


class IntelHpl(SpackApplication):
    '''Define HPL application using Intel MKL optimized binary from intel-oneapi-mpi package'''
    name = 'intel-hpl'

    maintainers('dodecatheon')

    tags('benchmark-app', 'benchmark', 'linpack', 'optimized', 'intel', 'mkl')

    define_compiler('gcc9', spack_spec='gcc@9.3.0')
    software_spec('imkl_2023p1', spack_spec='intel-oneapi-mkl@2023.1.0 threads=openmp', compiler='gcc9')
    software_spec('impi_2018', spack_spec='intel-mpi@2018.4.274')

    required_package('intel-oneapi-mkl')

    executable('execute',
               '{intel-oneapi-mkl}/mkl/latest/benchmarks/mp_linpack/xhpl_intel64_dynamic',
               use_mpi=True)

    workload('standard', executables=['execute'])
    workload('calculator', executables=['execute'])

    workload_variable('output_file',
                      default=pad_value('HPL.out', 'output file name (if any)'),
                      description='Output file name (if any)',
                      workloads=['standard'])
    workload_variable('device_out',
                      default=pad_value('6', 'device out (6=stdout,7=stderr,file)'),
                      description='Output device',
                      workloads=['standard'])
    workload_variable('N-Ns',
                      default=pad_value('4', 'Number of problems sizes (N)'),
                      description='Number of problems sizes',
                      workloads=['standard'])
    workload_variable('Ns',
                      default=pad_value('29 30 34 35', 'Ns'),
                      description='Problem sizes',
                      workloads=['standard'])
    workload_variable('N-NBs',
                      default=pad_value('4', 'Number of NBs'),
                      description='Number of NBs',
                      workloads=['standard'])
    workload_variable('NBs',
                      default=pad_value('1 2 3 4', 'NBs'),
                      description='NB values',
                      workloads=['standard'])
    workload_variable('PMAP',
                      default=pad_value('0', 'PMAP process mapping (0=Row-,1=Column-major)'),
                      description='PMAP Process mapping. (0=Row-, 1=Column-Major)',
                      workloads=['standard'])
    workload_variable('N-Grids',
                      default=pad_value('3', 'Number of process grids (P x Q)'),
                      description='Number of process grids (P x Q)',
                      workloads=['standard'])
    workload_variable('Ps',
                      default=pad_value('2 1 4', 'Ps'),
                      description='P values',
                      workloads=['standard'])
    workload_variable('Qs',
                      default=pad_value('2 4 1', 'Qs'),
                      description='Q values',
                      workloads=['standard'])
    workload_variable('threshold',
                      default=pad_value('16.0', 'threshold'),
                      description='Residual threshold',
                      workloads=['standard'])
    workload_variable('NPFACTs',
                      default=pad_value('3', 'Number of PFACTs, panel fact'),
                      description='Number of PFACTs',
                      workloads=['standard'])
    workload_variable('PFACTs',
                      default=pad_value('0 1 2', 'PFACTs (0=left, 1=Crout, 2=Right)'),
                      description='PFACT Values',
                      workloads=['standard'])
    workload_variable('N-NBMINs',
                      default=pad_value('2', 'Number of NBMINs, recursive stopping criteria'),
                      description='Number of NBMINs',
                      workloads=['standard'])
    workload_variable('NBMINs',
                      default=pad_value('2 4', 'NBMINs (>= 1)'),
                      description='NBMIN values',
                      workloads=['standard'])
    workload_variable('N-NDIVs',
                      default=pad_value('1', 'Number of NDIVs, panels in recursion'),
                      description='Number of NDIVs',
                      workloads=['standard'])
    workload_variable('NDIVs',
                      default=pad_value('2', 'NDIVs'),
                      description='NDIV values',
                      workloads=['standard'])
    workload_variable('N-RFACTs',
                      default=pad_value('3', 'Number of RFACTs, recursive panel fact.'),
                      description='Number of RFACTs',
                      workloads=['standard'])
    workload_variable('RFACTs',
                      default=pad_value('0 1 2', 'RFACTs (0=left, 1=Crout, 2=Right)'),
                      description='RFACT values',
                      workloads=['standard'])
    workload_variable('N-BCASTs',
                      default=pad_value('1', 'Number of BCASTs, broadcast'),
                      description='Number of BCASTs',
                      workloads=['standard'])
    workload_variable('BCASTs',
                      default=pad_value('0', 'BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM)'),
                      description='BCAST values',
                      workloads=['standard'])
    workload_variable('N-DEPTHs',
                      default=pad_value('1', 'Number of DEPTHs, lookahead depth'),
                      description='Number of DEPTHs',
                      workloads=['standard'])
    workload_variable('DEPTHs',
                      default=pad_value('0', 'DEPTHs (>=0)'),
                      description='DEPTH values',
                      workloads=['standard'])
    workload_variable('SWAP',
                      default=pad_value('2', 'SWAP (0=bin-exch,1=long,2=mix)'),
                      description='Swapping algorithm',
                      workloads=['standard'])
    workload_variable('swapping_threshold',
                      default=pad_value('64', 'swapping threshold'),
                      description='Swapping threshold',
                      workloads=['standard'])
    workload_variable('L1',
                      default=pad_value('0', 'L1 in (0=transposed,1=no-transposed) form'),
                      description='Storage for upper triangular portion of columns',
                      workloads=['standard'])
    workload_variable('U',
                      default=pad_value('0', 'U  in (0=transposed,1=no-transposed) form'),
                      description='Storage for the rows of U',
                      workloads=['standard'])
    workload_variable('Equilibration',
                      default=pad_value('1', 'Equilibration (0=no,1=yes)'),
                      description='Determines if equilibration should be enabled or disabled.',
                      workloads=['standard'])
    workload_variable('mem_alignment',
                      default=pad_value('8', 'memory alignment in double (> 0)'),
                      description='Sets the alignment in doubles for memory addresses',
                      workloads=['standard'])

    # calculator workload-specific variables:

    workload_variable('percent_mem', default='85',
                      description='Percent of memory to use (default 85)',
                      workloads=['calculator'])

    workload_variable('memory_per_node', default='240',
                      description='Memory per node in GB',
                      workloads=['calculator'])

    workload_variable('block_size', default='384',
                      description='Size of each block',
                      workloads=['calculator'])

    workload_variable('pfact', default='0',
                      description='PFACT for optimized calculator',
                      workloads=['calculator'])

    workload_variable('nbmin', default='2',
                      description='NBMIN for optimized calculator',
                      workloads=['calculator'])

    workload_variable('rfact', default='0',
                      description='RFACT for optimized calculator',
                      workloads=['calculator'])

    # Redefine default bcast to 6 for the MKL-optimized case
    workload_variable('bcast', default='6',
                      description='BCAST for Intel MKL optimized calculator',
                      workloads=['calculator'])

    workload_variable('depth', default='0',
                      description='DEPTH for optimized calculator',
                      workloads=['calculator'])

    # FOMs:
    log_str = os.path.join(Expander.expansion_str('experiment_run_dir'),
                           Expander.expansion_str('experiment_name') + '.out')

    figure_of_merit('Time', log_file=log_str,
                    fom_regex=r'.*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n',
                    group_name='time', units='s', contexts=['problem-name'])

    figure_of_merit('GFlops', log_file=log_str,
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

    def _calculate_values(self, workspace):
        expander = self.expander
        if expander.workload_name == 'calculator':
            # Find the best P and Q whose product is the number of available
            # cores, with P less than Q
            nNodes = int(expander.expand_var_name('n_nodes'))
            processesPerNode = int(expander.expand_var_name('processes_per_node'))

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
            memoryPerNode = int(expander.expand_var_name('memory_per_node'))
            memFraction = int(expander.expand_var_name('percent_mem')) / 100
            blockSize = int(expander.expand_var_name('block_size'))
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

            pfact = expander.expand_var_name('pfact')
            nbmin = expander.expand_var_name('nbmin')
            rfact = expander.expand_var_name('rfact')
            bcast = expander.expand_var_name('bcast')
            depth = expander.expand_var_name('depth')

            self.variables['N-Ns'] = pad_value('1', 'Number of problems sizes (N)')  # vs 4

            # Calculated:
            self.variables['Ns'] = pad_value(int(problemSize),
                                             f"Ns (= {usedPercentage}% of total available memory)")

            self.variables['N-NBs'] = pad_value('1', 'Number of NBs')  # vs 4

            # Calculated:
            self.variables['NBs'] = pad_value(blockSize, "NBs")  # calculated, vs 4 samples

            self.variables['N-Grids'] = pad_value('1', 'Number of Grids, process grids (P x Q)')  # vs 3

            # Calculated:
            self.variables['Ps'] = pad_value(int(bestP), "Ps")

            # Calculated:
            self.variables['Qs'] = pad_value(int(bestQ), "Qs")

            self.variables['NPFACTs'] = pad_value('1', 'Number of PFACTs, panel fact')  # vs 3

            # ramble.yaml configurable
            self.variables['PFACTs'] = pad_value(pfact, 'PFACT Values (0=left, 1=Crout, 2=Right)')  # vs 0 1 2

            self.variables['N-NBMINs'] = pad_value('1', 'Number of NBMINs, recursive stopping criteria')  # vs 2

            # ramble.yaml configurable
            self.variables['NBMINs'] = pad_value(nbmin, 'NBMINs (>= 1)')  # vs '2 4'

            self.variables['N-RFACTs'] = pad_value('1', 'Number of RFACTS, recursive panel fact.')  # vs '3'

            # ramble.yaml configurable
            self.variables['RFACTs'] = pad_value(rfact, 'RFACTs (0=left, 1=Crout, 2=Right)')  # vs '0 1 2'

            # ramble.yaml configurable
            self.variables['BCASTs'] = pad_value(bcast, 'BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM,6=MKL BPUSH,7=AMD Hybrid Panel)')  # vs '0'

            # ramble.yaml configurable
            self.variables['DEPTHs'] = pad_value(depth, 'DEPTHs (>=0)')  # vs '0'

    def _make_experiments(self, workspace, app_inst=None):
        super()._make_experiments(workspace)
        self._calculate_values(workspace)

        input_path = os.path.join(self.expander.expand_var_name('experiment_run_dir'),
                                  'HPL.dat')

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
                # This gets around an issue in expander where trailing comments
                # after '#' are not printed
                hash_replace_str = self.expander.expand_var_name(setting).replace('Number', '#')
                f.write(hash_replace_str + '\n')

            # Write some documentation at the bottom of the input file:
            f.write('##### This line (no. 32) is ignored (it serves as a separator). ######')
