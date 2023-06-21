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

    maintainers('douglasjacobsen')

    tags('molecular-dynamics')

    default_compiler('gcc9', spack_spec='gcc@9.3.0')

    software_spec('impi2018', spack_spec='intel-mpi@2018.4.274')

    software_spec('lammps',
                  spack_spec='lammps@20220623 +opt+manybody+molecule+kspace+rigid',
                  compiler='gcc9')

    required_package('lammps')

    input_file('leonard-jones', url='https://www.lammps.org/inputs/in.lj.txt', expand=False,
               sha256='874b4c63b6fcbb6ede76522df19087acf2f49b6bc96794cf0aa3218c66ff7e06',
               description='Atomic fluid. 32k atoms. 100 timesteps. https://www.lammps.org/bench.html#lj')
    input_file('eam', url='https://www.lammps.org/inputs/in.eam.txt', expand=False,
               sha256='2fa09183c626c34570cc367384fe4c297ab153521adb3ea44ff7e265d451ad75',
               description='Cu metallic solid with embedded atom method potential. 32k atoms. https://www.lammps.org/bench.html#eam')
    input_file('polymer-chain-melt', url='https://www.lammps.org/inputs/in.chain.txt', expand=False,
               sha256='97676f19d2d791c42415698c354a18b26a3cbe4006cd2161cf8924415d9f7c82',
               description='Bead-spring polymer melt with 100-mer chains and FENE bonds. 32k atoms. 100 timesteps. https://www.lammps.org/bench.html#chain')
    input_file('chute', url='https://www.lammps.org/inputs/in.chute.txt', expand=False,
               sha256='91e1743cc39365b32757cfb3c76399f5ed8debad0b890cb36ee7bdf47d2dfd2d',
               description='Chute flow of packed granular particles with frictional history potential. 32k atoms. 100 timeteps. https://www.lammps.org/bench.html#chute')
    input_file('rhodo', url='https://www.lammps.org/inputs/in.rhodo.txt', expand=False,
               sha256='4b6cc70db1b8fe269c48b8e06749f144f400e9a4054bf180ac9b1b9a5a5bb07f',
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

    workload_variable('input_path', default='{workload_input_dir}/in.{workload_name}.txt',
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
