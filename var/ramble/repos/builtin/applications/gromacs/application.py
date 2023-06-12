# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.appkit import *


class Gromacs(SpackApplication):
    '''Define a Gromacs application'''
    name = 'gromacs'

    maintainers('douglasjacobsen')

    tags('molecular-dynamics')

    default_compiler('gcc9', spack_spec='gcc@9.3.0')
    software_spec('impi2018', spack_spec='intel-mpi@2018.4.274')
    software_spec('gromacs', spack_spec='gromacs@2020.5', compiler='gcc9')

    executable('pre-process', 'gmx_mpi grompp ' +
               '-f {input_path}/{type}.mdp ' +
               '-c {input_path}/conf.gro ' +
               '-p {input_path}/topol.top ' +
               '-o exp_input.tpr', use_mpi=False)
    executable('execute-gen', 'gmx_mpi mdrun -notunepme -dlb yes ' +
               '-v -resethway -noconfout -nsteps 4000 ' +
               '-s exp_input.tpr', use_mpi=True)
    executable('execute', 'gmx_mpi mdrun -notunepme -dlb yes ' +
               '-v -resethway -noconfout -nsteps 4000 ' +
               '-s {input_path}', use_mpi=True)

    input_file('water_gmx50_bare', url='https://ftp.gromacs.org/pub/benchmarks/water_GMX50_bare.tar.gz',
               description='')
    input_file('water_bare_hbonds', url='https://ftp.gromacs.org/pub/benchmarks/water_bare_hbonds.tar.gz',
               description='')
    input_file('lignocellulose',
               url='https://repository.prace-ri.eu/ueabs/GROMACS/1.2/GROMACS_TestCaseB.tar.gz',
               description='A model of cellulose and lignocellulosic biomass in an aqueous ' +
                           'solution. This system of 3.3M atoms is inhomogeneous, at ' +
                           'least with GROMACS 4.5. This system uses reaction-field' +
                           'electrostatics instead of PME and therefore should scale well.')
    input_file('HECBioSim', url='https://github.com/victorusu/GROMACS_Benchmark_Suite/archive/refs/tags/1.0.0.tar.gz',
               description='https://www.hecbiosim.ac.uk/access-hpc/benchmarks')

    # input_file('BenchPEP', url='https://www.mpinat.mpg.de/632210/benchPEP.zip',
    #            description='12M Atoms, Peptides in Water, 2fs time step, all bonds constrained. https://www.mpinat.mpg.de/grubmueller/bench')

    input_file('BenchPEP', url='https://www.mpinat.mpg.de/benchPEP.zip',
               description='12M Atoms, Peptides in Water, 2fs time step, all bonds constrained. https://www.mpinat.mpg.de/grubmueller/bench')

    workload('water_gmx50', executables=['pre-process', 'execute-gen'],
             input='water_gmx50_bare')
    workload('water_bare', executables=['pre-process', 'execute-gen'],
             input='water_bare_hbonds')
    workload('lignocellulose', executables=['execute'],
             input='lignocellulose')
    workload('hecbiosim', executables=['execute'],
             input='HECBioSim')
    workload('benchpep', executables=['execute'],
             input='BenchPEP')

    workload_variable('size', default='1536',
                      description='Workload size',
                      workloads=['water_gmx50', 'water_bare'])
    workload_variable('type', default='pme',
                      description='Workload type. Valid values are ''pme'',''rf''',
                      workloads=['water_gmx50', 'water_bare'])
    workload_variable('input_path', default='{water_gmx50_bare}/{size}',
                      description='Input path for water GMX50',
                      workload='water_gmx50')
    workload_variable('input_path', default='{water_bare_hbonds}/{size}',
                      description='Input path for water bare hbonds',
                      workload='water_bare')
    workload_variable('input_path', default='{lignocellulose}/lignocellulose-rf.tpr',
                      description='Input path for lignocellulose',
                      workload='lignocellulose')
    workload_variable('type', default='Crambin',
                      description='Workload type. Valid values are ''Crambin'', ''Glutamine-Binding-Protein'', ''hEGFRDimer'', ''hEGFRDimerPair'', ''hEGFRDimerSmallerPL'', ''hEGFRtetramerPair''',
                      workload='hecbiosim')
    workload_variable('input_path', default='{HECBioSim}/HECBioSim/{type}/benchmark.tpr',
                      description='Input path for hecbiosim',
                      workload='hecbiosim')
    workload_variable('input_path', default='{BenchPEP}/benchPEP.tpr',
                      description='Input path for Bench PEP workload',
                      workload='benchpep')

    figure_of_merit('Core Time', log_file='{experiment_run_dir}/md.log',
                    fom_regex=r'\s+Time:\s+(?P<core_time>[0-9]+\.[0-9]+).*',
                    group_name='core_time', units='s')

    figure_of_merit('Wall Time', log_file='{experiment_run_dir}/md.log',
                    fom_regex=r'\s+Time:\s+[0-9]+\.[0-9]+\s+' +
                              r'(?P<wall_time>[0-9]+\.[0-9]+).*',
                    group_name='wall_time', units='s')

    figure_of_merit('Percent Core Time', log_file='{experiment_run_dir}/md.log',
                    fom_regex=r'\s+Time:\s+[0-9]+\.[0-9]+\s+[0-9]+\.[0-9]+\s+' +
                              r'(?P<perc_core_time>[0-9]+\.[0-9]+).*',
                    group_name='perc_core_time', units='%')

    figure_of_merit('Nanosecs per day', log_file='{experiment_run_dir}/md.log',
                    fom_regex=r'Performance:\s+' +
                              r'(?P<ns_per_day>[0-9]+\.[0-9]+).*',
                    group_name='ns_per_day', units='ns/day')

    figure_of_merit('Hours per nanosec', log_file='{experiment_run_dir}/md.log',
                    fom_regex=r'Performance:\s+[0-9]+\.[0-9]+\s+' +
                              r'(?P<hours_per_ns>[0-9]+\.[0-9]+).*',
                    group_name='hours_per_ns', units='hours/ns')
