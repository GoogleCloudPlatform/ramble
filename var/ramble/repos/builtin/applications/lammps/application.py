# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Lammps(SpackApplication):
    '''Define LAMMPS application'''
    name = 'lammps'

    tags = ['molecular-dynamics']

    default_compiler('gcc9', base='gcc', version='9.3.0')

    mpi_library('impi2018', base='intel-mpi', version='2018.4.274')

    software_spec('lammps', base='lammps', version='20220623',
                  compiler='gcc9', mpi='impi2018',
                  variants='+opt+manybody+molecule+kspace+rigid',
                  required=True)

    input_file('leonard-jones', url='https://www.lammps.org/inputs/in.lj.txt', expand=False,
               description='Atomic fluid. 32k atoms. 100 timesteps. https://www.lammps.org/bench.html#lj')
    input_file('eam', url='https://www.lammps.org/inputs/in.eam.txt', expand=False,
               description='Cu metallic solid with embedded atom method potential. 32k atoms. https://www.lammps.org/bench.html#eam')
    input_file('polymer-chain-melt', url='https://www.lammps.org/inputs/in.chain.txt', expand=False,
               description='Bead-spring polymer melt with 100-mer chains and FENE bonds. 32k atoms. 100 timesteps. https://www.lammps.org/bench.html#chain')
    input_file('chute', url='https://www.lammps.org/inputs/in.chute.txt', expand=False,
               description='Chute flow of packed granular particles with frictional history potential. 32k atoms. 100 timeteps. https://www.lammps.org/bench.html#chute')
    input_file('rhodo', url='https://www.lammps.org/inputs/in.rhodo.txt', expand=False,
               description='All-atom rhodopsin protein in solvated lipid bilayer with CHARMM force field, long-range Coulombics via PPPM (particle-particle particle mesh), SHAKE constraints. This model contains counter-ions and a reduced amount of water to make a 32K atom system. 32k atoms. 100 timesteps. https://www.lammps.org/bench.html#rhodo')

    executable('copy', template=['cp {input_path} {experiment_run_dir}/input.txt'],
               use_mpi=False)
    executable('set-size',
               template=["sed -i -e 's/xx equal .*/xx equal {xx}/g' -i input.txt",
                         "sed -i -e 's/yy equal .*/yy equal {yy}/g' -i input.txt",
                         "sed -i -e 's/zz equal .*/zz equal {zz}/g' -i input.txt"],
               use_mpi=False)
    executable('set-timesteps',
               template=["sed 's/run.*[0-9]+/run\t\t{timesteps}/g' -i input.txt"],
               use_mpi=False)
    executable('execute', '{lammps}/bin/lmp -i input.txt', use_mpi=True)

    workload('lj', executables=['copy', 'set-size', 'set-timesteps', 'execute'],
             input='leonard-jones')
    workload('eam', executables=['copy', 'set-size', 'set-timesteps', 'execute'],
             input='eam')
    workload('chain', executables=['copy', 'set-timesteps', 'execute'],
             input='polymer-chain-melt')
    workload('chute', executables=['copy', 'set-timesteps', 'execute'],
             input='chute')
    workload('rhodo', executables=['copy', 'set-timesteps', 'execute'],
             input='rhodo')

    workload_variable('xx', default='20*$x',
                      description='Number of atoms in the x direction',
                      workloads=['lj', 'eam'])
    workload_variable('yy', default='20*$y',
                      description='Number of atoms in the y direction',
                      workloads=['lj', 'eam'])
    workload_variable('zz', default='20*$z',
                      description='Number of atoms in the z direction',
                      workloads=['lj', 'eam'])
    workload_variable('timesteps', default='100',
                      description='Number of timesteps',
                      workloads=['lj', 'eam', 'polymer-chain-melt', 'chute', 'rhodo'])

    workload_variable('input_path', default='{application_input_dir}/in.{workload_name}.txt',
                      description='Path for the workload input file.',
                      workloads=['lj', 'eam', 'chain', 'chute', 'rhodo'])

    figure_of_merit('Nanoseconds per day', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'Performance: (?P<nspd>[0-9]+\.[0-9]*) tau/day, (?P<tsps>[0-9]+\.[0-9]*) timesteps/s',
                    group_name='nspd', units='ns/day')
    figure_of_merit('Timesteps per second', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'Performance: (?P<nspd>[0-9]+\.[0-9]*) tau/day, (?P<tsps>[0-9]+\.[0-9]*) timesteps/s',
                    group_name='tsps', units='timesteps/s')
    figure_of_merit('Wallclock time', log_file='{experiment_run_dir}/{experiment_name}.out',
                    fom_regex=r'Total wall time: (?P<walltime>[0-9]+:[0-9]+:[0-9]+)',
                    group_name='walltime', units='')
