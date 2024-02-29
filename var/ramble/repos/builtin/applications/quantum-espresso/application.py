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


class QuantumEspresso(SpackApplication):
    '''Define Quantum-Espresso application.'''
    name = 'quantum-espresso'

    maintainers('douglasjacobsen')

    tags('electronic-structure', 'materials', 'dft', 'density-functional-theory', 'plane-waves', 'pseudopotentials')

    define_compiler('gcc13', spack_spec='gcc@13.1.0')

    software_spec('impi2021p8', spack_spec='intel-oneapi-mpi@2021.8.0')
    software_spec('quantum-espresso', spack_spec='quantum-espresso@7.1', compiler='gcc13')

    required_package('quantum-espresso')

    input_file('AUSURF112', url='https://github.com/QEF/benchmarks/releases/download/bench0.0/AUSURF112.tgz',
               sha256='2b71c27801f8abbde05f48297b56b3194be0f83be50c50433f44bb886cac5117',
               description='Input file for AUSURF112 benchmark')

    input_file('CNT10POR8', url='https://github.com/QEF/benchmarks/releases/download/bench0.0/CNT10POR8.tgz',
               sha256='65e36acd332c1511cfa9cbdab0170a867b3144c98103c5bff3c5621ef795c00a',
               description='Input file for CNT10POR8 benchmark')

    input_file('GRIR443', url='https://github.com/QEF/benchmarks/releases/download/bench0.0/GRIR443.tgz',
               sha256='18016da632cde8624faeb07f3de04151a02f3b885aa4cbc111d6b912215403f8',
               description='Input file for GRIR443 benchmark')

    input_file('GRIR686', url='https://github.com/QEF/benchmarks/releases/download/bench0.0/GRIR686.tgz',
               sha256='4ade7691f88dd322b41abecbc08cc55437f9d376142e62b615317598abe498d7',
               description='Input file for GRIR686 benchmark')

    input_file('PSIWAT', url='https://github.com/QEF/benchmarks/releases/download/bench0.0/PSIWAT.tgz',
               sha256='698fbdac9f307b9ebc77e70e52574d67adb0f21bfd6874559d633471664b77d6',
               description='Input file for PSIWAT benchmark')

    input_file('WATER_EXX', url='https://raw.githubusercontent.com/QEF/benchmarks/master/other-inputs/water/pw.in',
               sha256='20a20b2f9370103cc62b97367b36d95017a4e9330b693fefe8742c345e963bbc',
               expand=False,
               description='Input file for WATER_EXX benchmark')

    input_file('WATER_EXX_H', url='https://raw.githubusercontent.com/QEF/benchmarks/master/other-inputs/water/pseudo/H.pbe-mt_fhi.UPF',
               sha256='124e26c52bc3ccaa24012895ad5f4902e1f646546a3477be7e7e6080a2f6b3af',
               expand=False,
               description='H Pseudopotential for WATER_EXX benchmark')

    input_file('WATER_EXX_O', url='https://raw.githubusercontent.com/QEF/benchmarks/master/other-inputs/water/pseudo/O.pbe-mt_fhi.UPF',
               sha256='436751b1fe7bb83e647fb1a9d754d2d9c1057e7df6243811fc8ca266f5f74fc8',
               expand=False,
               description='O Pseudopotential for WATER_EXX benchmark')

    executable('copy_inputs', 'cp ' + os.path.join(Expander.expansion_str('input_path'), '*') + ' '
               + os.path.join(Expander.expansion_str('experiment_run_dir'), '.'),
               use_mpi=False)
    executable('copy_potential1',
               template=[
                   'mkdir -p {experiment_run_dir}/pseudo',
                   'cp {potential1} {experiment_run_dir}/pseudo/.'
               ],
               use_mpi=False)
    executable('copy_potential2',
               template=[
                   'mkdir -p {experiment_run_dir}/pseudo',
                   'cp {potential2} {experiment_run_dir}/pseudo/.'
               ],
               use_mpi=False)

    executable('execute', 'pw.x {flags} < {input_file}', use_mpi=True)

    workload_names = ['AUSURF112', 'CNT10POR8', 'GRIR443', 'GRIR686', 'PSIWAT']
    input_files = ['ausurf.in', 'pw.in', 'grir443.in', 'grir686.in', 'psiwat.in']
    for wl_name, input_file in zip(workload_names, input_files):
        workload(wl_name, executables=['copy_inputs', 'execute'], inputs=[wl_name])
        workload_variable('input_path', default=Expander.expansion_str(wl_name),
                          description='Path to inputs for ' + wl_name + ' workload',
                          workloads=[wl_name])
        workload_variable('input_file', default=input_file,
                          description='Name of input file for ' + wl_name + ' workload',
                          workloads=[wl_name])
        workload_variable('flags', default='',
                          description='Flags for Quantum Espresso',
                          workloads=[wl_name])

    workload('WATER_EXX', executables=['copy_potential1', 'copy_potential2', 'execute'],
             inputs=['WATER_EXX', 'WATER_EXX_H', 'WATER_EXX_O'])
    workload_variable('input_file', default=Expander.expansion_str('WATER_EXX'),
                      description='Path to WATER_EXX input',
                      workloads=['WATER_EXX'])
    workload_variable('potential1', default=Expander.expansion_str('WATER_EXX_H'),
                      description='Path to WATER_EXX H potential file',
                      workloads=['WATER_EXX'])
    workload_variable('potential2', default=Expander.expansion_str('WATER_EXX_O'),
                      description='Path to WATER_EXX O potential file',
                      workloads=['WATER_EXX'])

    workload_variable('flags', default='',
                      description='Flags for Quantum Espresso',
                      workloads=['WATER_EXX'])

    log_str = Expander.expansion_str('log_file')
    figure_of_merit('Total CPU time',
                    fom_regex=r'\s*total cpu time spent up to now is\s+(?P<time>[0-9]+\.[0-9]+).*',
                    group_name='time', log_file=log_str, units='s')

    figure_of_merit('Estimated SCF accuracy',
                    fom_regex=r'\s*estimated scf accuracy\s+<\s+(?P<energy>[0-9]+\.[0-9]+).*',
                    group_name='energy', log_file=log_str, units='Ry')

    profile_regex = r'\s+(?P<section>[\w:]+)\s+:\s+(?P<cpu>[0-9]+\.[0-9]+)s CPU\s+' + \
                    r'(?P<wall>[0-9]+\.[0-9]+)s WALL \(\s+(?P<calls>[0-9]+) calls\).*'
    figure_of_merit_context('Profile section', regex=profile_regex,
                            output_format='{section}')

    figure_of_merit('Section CPU Time', fom_regex=profile_regex,
                    group_name='cpu', log_file=log_str, units='s',
                    contexts=['Profile section'])

    figure_of_merit('Section Wall Time', fom_regex=profile_regex,
                    group_name='wall', log_file=log_str, units='s',
                    contexts=['Profile section'])

    figure_of_merit('Section Number of Calls', fom_regex=profile_regex,
                    group_name='calls', log_file=log_str, units='',
                    contexts=['Profile section'])

    success_criteria('job_done', mode='string',
                     match=r'.*JOB DONE\..*',
                     file=log_str)
